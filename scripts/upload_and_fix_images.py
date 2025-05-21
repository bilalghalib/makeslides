#!/usr/bin/env python3
"""
MakeSlides Image Uploader and Fixer

This script:
1. Identifies and uploads diagram images by examining both JSON and markdown
2. Replaces local image references with remote URLs
3. Creates a properly formatted slides presentation

Usage: python upload_and_fix_images.py slides_your_file.md
"""

import os
import sys
import re
import json
import logging
import argparse
import subprocess
import tempfile
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("image_fixer")

def read_file(file_path):
    """Read file contents safely."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

def write_file(file_path, content):
    """Write content to file safely."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {e}")
        return False

def validate_image_path(img_path):
    """Validate that an image exists and is readable."""
    if not os.path.exists(img_path):
        logger.error(f"Image not found: {img_path}")
        return False
    
    # Test file readability
    try:
        with open(img_path, 'rb') as f:
            f.read(1)
        return True
    except Exception as e:
        logger.error(f"Cannot read image {img_path}: {e}")
        return False

def upload_image_with_retry(img_path, expiry_time="24h", max_retries=3):
    """Upload an image with retry logic for resilience."""
    for attempt in range(max_retries):
        try:
            result = upload_image(img_path, expiry_time)
            if result:
                return result
            # Wait before retrying
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Upload attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying upload... ({attempt+2}/{max_retries})")
                time.sleep(2 ** attempt)
            else:
                logger.error(f"All upload attempts failed for {img_path}")
    return None

def upload_image(img_path, expiry_time="24h"):
    """Upload an image to litterbox.catbox.moe."""
    # Validate the image path
    if not validate_image_path(img_path):
        return None
    
    # Determine if path is relative to 'images/' directory
    if not img_path.startswith('images/') and not os.path.exists(img_path):
        img_path = f"images/{os.path.basename(img_path)}"
        if not validate_image_path(img_path):
            return None
    
    logger.info(f"Uploading {img_path}...")
    
    try:
        # Direct curl command to litterbox
        cmd = f'curl -s -F "reqtype=fileupload" -F "time={expiry_time}" -F "fileToUpload=@{img_path}" https://litterbox.catbox.moe/resources/internals/api.php'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        
        output = result.stdout.strip()
        if output.startswith("https://litter.catbox.moe/"):
            logger.info(f"✅ Uploaded {img_path} -> {output}")
            return output
        else:
            logger.warning(f"Upload failed with response: {output}")
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running upload command for {img_path}: {e}")
        logger.error(f"Stderr: {e.stderr}")
        return None

def find_diagrams_from_json(json_file, base_dir):
    """Find all diagrams referenced in a JSON file with improved path handling."""
    if not os.path.exists(json_file):
        logger.warning(f"JSON file not found: {json_file}")
        return []
    
    # Normalize paths for consistent comparison
    base_dir = os.path.abspath(base_dir)
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        diagrams = []
        
        # Handle different JSON structures
        slides = []
        if isinstance(data, dict) and "slides" in data:
            slides = data["slides"]
        elif isinstance(data, list):
            slides = data
        else:
            logger.warning(f"Unrecognized JSON structure in {json_file}")
            return []
        
        # Extract the base name for diagram naming patterns
        base_name = os.path.basename(json_file).replace("slides_", "").replace(".json", "")
        logger.debug(f"Base name for diagrams: {base_name}")
        
        # Find all diagram references with improved pattern matching
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            
            slide_num = slide.get("slide_number", 0)
            
            # Check for diagram content
            if slide.get("diagram_type") and slide.get("diagram_type") != "null":
                diagram_type = slide.get("diagram_type")
                
                # Try multiple naming patterns for diagrams
                patterns = [
                    # Standard pattern with diagram type
                    f"images/{base_name}_slide{slide_num}_{diagram_type}.png",
                    # Simple slide number only
                    f"images/{base_name}_slide{slide_num}.png",
                    # Alternative with file extension in name
                    f"images/{base_name}.md_slide{slide_num}.png",
                    # Just slide number in images dir
                    f"images/slide{slide_num}.png",
                    # With diagram type
                    f"images/slide{slide_num}_{diagram_type}.png"
                ]
                
                found = False
                for pattern in patterns:
                    full_path = os.path.join(base_dir, pattern)
                    if os.path.exists(full_path):
                        diagrams.append({
                            "slide_number": slide_num,
                            "type": diagram_type,
                            "path": full_path,
                            "pattern_used": pattern
                        })
                        logger.info(f"Found diagram for slide {slide_num}: {pattern}")
                        found = True
                        break
                
                if not found:
                    # Last resort: search for any image with this slide number
                    images_dir = os.path.join(base_dir, "images")
                    if os.path.exists(images_dir):
                        for filename in os.listdir(images_dir):
                            if f"slide{slide_num}" in filename and filename.endswith(".png"):
                                full_path = os.path.join(images_dir, filename)
                                diagrams.append({
                                    "slide_number": slide_num,
                                    "type": diagram_type,
                                    "path": full_path,
                                    "pattern_used": f"images/{filename}"
                                })
                                logger.info(f"Found alternative diagram for slide {slide_num}: {filename}")
                                found = True
                                break
                
                if not found:
                    logger.warning(f"No diagram found for slide {slide_num}")
            
            # Check for image_url references
            if slide.get("image_url") and slide.get("image_url") != "null":
                image_url = slide.get("image_url")
                
                # Only process local paths, not remote URLs
                if isinstance(image_url, str) and not image_url.startswith(("http://", "https://")):
                    # Handle both absolute and relative paths
                    if not os.path.isabs(image_url):
                        img_path = os.path.join(base_dir, image_url)
                    else:
                        img_path = image_url
                        
                    # Verify path exists, try alternatives if needed
                    if os.path.exists(img_path):
                        diagrams.append({
                            "slide_number": slide_num,
                            "type": "image",
                            "path": img_path,
                            "pattern_used": image_url
                        })
                        logger.info(f"Found image for slide {slide_num}: {img_path}")
                    else:
                        # Try with images/ prefix if not already present
                        if "images/" not in image_url.lower():
                            alt_path = os.path.join(base_dir, "images", os.path.basename(image_url))
                            if os.path.exists(alt_path):
                                diagrams.append({
                                    "slide_number": slide_num,
                                    "type": "image",
                                    "path": alt_path,
                                    "pattern_used": f"images/{os.path.basename(image_url)}"
                                })
                                logger.info(f"Found alternative image for slide {slide_num}: {alt_path}")
                            else:
                                logger.warning(f"Image not found for slide {slide_num}: {image_url}")
                        else:
                            logger.warning(f"Image not found for slide {slide_num}: {image_url}")
        
        return diagrams
    except Exception as e:
        logger.error(f"Error processing JSON file: {e}")
        return []

def find_markdown_images(md_file):
    """Find all image references in a markdown file with improved path handling."""
    try:
        content = read_file(md_file)
        if not content:
            return []
        
        # Find markdown image syntax: ![alt text](path)
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = re.findall(img_pattern, content)
        
        if not matches:
            logger.warning(f"No image references found in {md_file}")
            return []
            
        logger.info(f"Found {len(matches)} image references in {md_file}")
        
        images = []
        base_dir = os.path.dirname(md_file)
        
        for alt_text, img_path in matches:
            # Skip if already an http URL
            if img_path.startswith(("http://", "https://")):
                logger.info(f"Skipping remote URL: {img_path}")
                continue
                
            # Handle relative paths
            if not os.path.isabs(img_path):
                full_path = os.path.join(base_dir, img_path)
            else:
                full_path = img_path
                
            # Check if the file exists
            if os.path.exists(full_path):
                images.append({
                    "alt_text": alt_text,
                    "path": full_path,
                    "reference": f"![{alt_text}]({img_path})"
                })
                logger.info(f"Found image reference in markdown: {img_path}")
            else:
                # Try alternative paths
                alt_path = os.path.join(base_dir, "images", os.path.basename(img_path))
                if os.path.exists(alt_path):
                    images.append({
                        "alt_text": alt_text,
                        "path": alt_path,
                        "reference": f"![{alt_text}]({img_path})"
                    })
                    logger.info(f"Found image at alternative path: {alt_path}")
                else:
                    logger.warning(f"Referenced image not found: {img_path}")
        
        return images
    except Exception as e:
        logger.error(f"Error processing markdown file: {e}")
        return []

def scan_directory_for_images(base_dir, prefix=None):
    """Scan directory for any potentially relevant images with improved pattern matching."""
    images_dir = os.path.join(base_dir, "images")
    if not os.path.exists(images_dir):
        logger.warning(f"Images directory not found: {images_dir}")
        return []
        
    potential_images = []
    
    for filename in os.listdir(images_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
            # If a prefix is specified, only include files that match the pattern
            if prefix and not (filename.startswith(prefix) or "slide" in filename):
                continue
                
            image_path = os.path.join(images_dir, filename)
            
            # Try to extract slide number from filename
            slide_match = re.search(r'slide(\d+)', filename)
            slide_num = int(slide_match.group(1)) if slide_match else 0
            
            # Try to extract diagram type from filename
            type_match = re.search(r'_(flowchart|mindmap|pie|classDiagram|timeline|sequence)', filename)
            diagram_type = type_match.group(1) if type_match else "diagram"
            
            potential_images.append({
                "path": image_path,
                "filename": filename,
                "slide_number": slide_num,
                "type": diagram_type
            })
    
    logger.info(f"Found {len(potential_images)} potential images in {images_dir}")
    return potential_images

def update_markdown_with_remote_urls(md_file, replacements):
    """Update markdown file with remote image URLs with improved replacement logic."""
    if not replacements:
        logger.info("No replacements to make")
        return False
    
    content = read_file(md_file)
    if not content:
        return False
        
    original_content = content
    
    # Create a backup of the original
    backup_path = f"{md_file}.original"
    if not write_file(backup_path, original_content):
        logger.warning("Failed to create backup file")
    else:
        logger.info(f"Created backup at {backup_path}")
    
    # Apply each replacement
    for local_path, remote_url in replacements.items():
        # Include variations of the path to ensure all references are updated
        variations = [
            re.escape(local_path),
            re.escape(os.path.relpath(local_path, os.path.dirname(md_file))),
            re.escape(os.path.basename(local_path)),
            re.escape(f"images/{os.path.basename(local_path)}")
        ]
        
        for variation in variations:
            pattern = f'!\\[[^\\]]*\\]\\({variation}\\)'
            replacement = f'![Image]({remote_url})'
            
            # Apply the replacement
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                logger.info(f"Replaced {variation} with {remote_url}")
    
    # Save the changes if content was modified
    if content != original_content:
        if write_file(md_file, content):
            logger.info(f"Updated {md_file} with remote image URLs")
            
            # Check if there are still any local image references
            local_refs = re.findall(r'!\[[^\]]*\]\([^(http)][^)]+\)', content)
            if local_refs:
                logger.warning(f"There are still {len(local_refs)} local image references that couldn't be replaced")
                for ref in local_refs[:5]:  # Show just the first few
                    logger.warning(f"  {ref}")
            
            return True
    else:
        logger.warning("No changes were made to the markdown file")
        
        # If markdown wasn't changed but we have replacements, add them at the end
        if replacements:
            logger.info("Adding unreferenced images at the end of the file")
            appended_content = content + "\n\n<!-- Additional images -->\n"
            added = 0
            
            for local_path, remote_url in replacements.items():
                # Only add images that aren't already in the content
                if remote_url not in content:
                    appended_content += f"\n![Image]({remote_url})\n"
                    added += 1
            
            if added > 0:
                if write_file(md_file, appended_content):
                    logger.info(f"Appended {added} missing images to {md_file}")
                    return True
    
    return False

def run_md2gslides(md_file, title_prefix="", use_fileio=True):
    """Run md2gslides to generate the presentation with improved error handling."""
    title = os.path.basename(md_file).replace('.md', '')
    
    logger.info(f"Generating presentation for {md_file}")
    
    # Verify md2gslides is installed
    try:
        subprocess.run(["md2gslides", "--version"], 
                      stderr=subprocess.DEVNULL, 
                      stdout=subprocess.DEVNULL, 
                      check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("md2gslides might not be installed. Attempting to run anyway.")
    
    # Build the command
    cmd = ["md2gslides"]
    if title_prefix:
        cmd.extend(["--title", f"{title_prefix} {title}"])
    else:
        cmd.extend(["--title", title])
    
    if use_fileio:
        cmd.append("--use-fileio")
    
    cmd.append(md_file)
    
    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Check for the presentation URL
        url_match = re.search(r'Opening your presentation \((https://docs\.google\.com/[^)]+)\)', result.stdout)
        if url_match:
            url = url_match.group(1)
            logger.info(f"Presentation created: {url}")
            
            # Save URL to file
            output_file = f"{os.path.splitext(md_file)[0]}-presentation.txt"
            if write_file(output_file, url):
                logger.info(f"Saved presentation URL to {output_file}")
            
            return url
        else:
            logger.warning("Could not find presentation URL in output")
            logger.debug(f"Output: {result.stdout}")
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running md2gslides: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        
        # Special handling for specific errors
        if "No slides found" in e.stderr:
            logger.error("md2gslides couldn't find valid slides in the markdown file")
            logger.info("Try running 'python format-markdown.py' on the file first")
        elif "Authentication required" in e.stderr:
            logger.error("md2gslides authentication failed")
            logger.info("Try running 'md2gslides --auth' to set up authentication")
        elif "network" in e.stderr.lower():
            logger.error("Network error when running md2gslides")
            logger.info("Check your internet connection and try again")
        
        return None

def main():
    parser = argparse.ArgumentParser(description="Fix images in slides and generate presentation")
    parser.add_argument("markdown_file", help="Path to the markdown file")
    parser.add_argument("--expiry", choices=["1h", "12h", "24h", "72h"], default="24h",
                        help="Expiry time for uploaded images (default: 24h)")
    parser.add_argument("--title-prefix", default="", help="Prefix for presentation title")
    parser.add_argument("--no-fileio", action="store_true", help="Don't use file.io for uploads")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-slides", action="store_true", help="Don't create Google Slides presentation")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        
    # Check if markdown file exists
    md_file = args.markdown_file
    if not os.path.exists(md_file):
        logger.error(f"Markdown file not found: {md_file}")
        sys.exit(1)
    
    # Find the corresponding JSON file
    base_dir = os.path.dirname(md_file)
    base_name = os.path.basename(md_file)
    base_name_no_ext = os.path.splitext(base_name)[0]
    
    # If the filename starts with "slides_", look for matching JSON
    if base_name.startswith("slides_"):
        source_name = base_name.replace("slides_", "").replace(".md", "")
        json_file = os.path.join(base_dir, f"slides_{source_name}.json")
    else:
        # Otherwise guess based on file name
        json_file = os.path.join(base_dir, f"slides_{base_name_no_ext}.json")
        # Fallback for simpler JSON
        if not os.path.exists(json_file):
            json_file = os.path.join(base_dir, f"{base_name_no_ext}.json")
    
    # Report on JSON file status
    if os.path.exists(json_file):
        logger.info(f"Found JSON file: {json_file}")
    else:
        logger.warning(f"JSON file not found: {json_file}")
        logger.info("Will only use markdown references")
    
    # List of all images to process and upload
    all_images = []
    
    # 1. Find images referenced in the JSON
    if os.path.exists(json_file):
        json_diagrams = find_diagrams_from_json(json_file, base_dir)
        all_images.extend(json_diagrams)
    
    # 2. Find images referenced in the markdown
    md_images = find_markdown_images(md_file)
    
    # Add only images that aren't already in the list
    for md_image in md_images:
        if not any(img.get('path') == md_image.get('path') for img in all_images):
            all_images.append(md_image)
    
    # 3. If still no images found, scan directory for all possible images
    if not all_images:
        logger.warning("No images found in JSON or markdown. Scanning directory...")
        source_name = source_name if 'source_name' in locals() else None
        potential_images = scan_directory_for_images(base_dir, source_name)
        all_images.extend(potential_images)
    
    if not all_images:
        logger.warning("No images found to process")
        
        # Try to run md2gslides anyway in case it works without images
        if not args.no_slides:
            url = run_md2gslides(md_file, args.title_prefix, not args.no_fileio)
            
            if url:
                print(f"\n✅ Presentation created (without images): {url}\n")
            else:
                print("\n⚠️ Failed to create presentation\n")
        
        sys.exit(0)
    
    # Upload all images and create replacements map
    logger.info(f"Uploading {len(all_images)} images...")
    replacements = {}
    
    for image in all_images:
        path = image.get("path")
        if not path:
            continue
            
        # Skip if we've already uploaded this image
        if path in replacements:
            continue
            
        # Skip if it's already a remote URL
        if isinstance(path, str) and path.startswith(('http://', 'https://')):
            continue
            
        # Upload the image with retry logic
        remote_url = upload_image_with_retry(path, args.expiry)
        if remote_url:
            replacements[path] = remote_url
            logger.info(f"✓ Uploaded: {path} -> {remote_url}")
        else:
            logger.error(f"✗ Failed to upload: {path}")
    
    # Update the markdown with the remote URLs
    updated = update_markdown_with_remote_urls(md_file, replacements)
    
    # Run md2gslides to create the presentation
    if not args.no_slides:
        url = run_md2gslides(md_file, args.title_prefix, not args.no_fileio)
        
        if url:
            print(f"\n✅ Presentation created and available at: {url}\n")
            print(f"Note: Uploaded images will expire after {args.expiry}")
        else:
            print("\n⚠️ Failed to create presentation or retrieve URL\n")
    else:
        if updated:
            print(f"\n✅ Markdown updated with remote image URLs\n")
            print(f"Note: Uploaded images will expire after {args.expiry}")
        else:
            print("\n⚠️ No updates were made to the markdown file\n")

if __name__ == "__main__":
    main()