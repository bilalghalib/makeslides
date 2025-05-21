#!/usr/bin/env python3
"""
Direct Image Fixer for MakeSlides

This script takes a direct approach to fixing image issues in slides:

1. Finds local image references in markdown files
2. Uploads them to litterbox.catbox.moe
3. Replaces references with remote URLs
4. Processes the markdown with md2gslides

Usage: python direct_image_fixer.py slides_your_file.md
"""

import os
import sys
import re
import logging
import argparse
import subprocess
import tempfile
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("direct_image_fixer")

def read_file(file_path):
    """Read file contents."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path, content):
    """Write content to file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def upload_image(img_path, expiry_time="24h"):
    """Upload an image to litterbox.catbox.moe."""
    if not os.path.exists(img_path):
        logger.warning(f"Image not found: {img_path}")
        return None
    
    # Determine if path is relative to 'images/' directory
    if not img_path.startswith('images/') and not os.path.exists(img_path):
        img_path = f"images/{img_path}"
        if not os.path.exists(img_path):
            logger.warning(f"Image still not found at: {img_path}")
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
            logger.warning(f"Upload failed: {output}")
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error uploading {img_path}: {e}")
        return None

def process_markdown(md_path, expiry_time="24h"):
    """Process markdown file to fix image references."""
    logger.info(f"Processing {md_path}")
    
    content = read_file(md_path)
    original_content = content
    
    # Find all image references
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(image_pattern, content)
    
    if not matches:
        logger.info("No image references found")
        return md_path
    
    logger.info(f"Found {len(matches)} image references")
    
    # Create a temporary markdown file
    temp_dir = tempfile.mkdtemp()
    temp_md = os.path.join(temp_dir, os.path.basename(md_path))
    
    # Process each image reference
    replacements = {}
    for alt_text, img_path in matches:
        # Skip if already an http URL
        if img_path.startswith("http"):
            logger.info(f"Skipping already remote image: {img_path}")
            continue
        
        # Upload the image
        remote_url = upload_image(img_path, expiry_time)
        if remote_url:
            replacements[img_path] = remote_url
    
    # Replace all image references
    for local_path, remote_url in replacements.items():
        # Escape special regex characters in the local path
        escaped_path = re.escape(local_path)
        # Replace with the remote URL
        content = re.sub(f'!\\[([^\\]]*)\\]\\({escaped_path}\\)', f'![\\1]({remote_url})', content)
    
    # Save the modified content if changes were made
    if content != original_content:
        logger.info(f"Replaced {len(replacements)} image references")
        
        # Create a backup of the original
        backup_path = f"{md_path}.bak"
        write_file(backup_path, original_content)
        logger.info(f"Original saved to {backup_path}")
        
        # Save the modified content
        write_file(md_path, content)
        logger.info(f"Updated {md_path} with remote image URLs")
    else:
        logger.warning("No changes were made to the file")
    
    return md_path

def run_md2gslides(md_path, title_prefix="", use_fileio=True):
    """Run md2gslides to create the presentation."""
    logger.info(f"Creating presentation with md2gslides: {md_path}")
    
    # Get the base name for the presentation title
    title = os.path.basename(md_path).replace('.md', '')
    
    # Prepare the md2gslides command
    cmd = ["md2gslides"]
    if title_prefix:
        cmd.extend(["--title", f"{title_prefix} {title}"])
    else:
        cmd.extend(["--title", title])
    
    # Add --use-fileio if needed
    if use_fileio:
        cmd.append("--use-fileio")
    
    # Add the markdown file path
    cmd.append(md_path)
    
    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Extract the presentation URL
        url_match = re.search(r'Opening your presentation \((https://docs\.google\.com/[^)]+)\)', result.stdout)
        if url_match:
            presentation_url = url_match.group(1)
            logger.info(f"Presentation created: {presentation_url}")
            
            # Save the URL to a file
            output_file = f"{os.path.splitext(md_path)[0]}-presentation.txt"
            with open(output_file, 'w') as f:
                f.write(presentation_url)
            logger.info(f"Presentation URL saved to {output_file}")
            
            return presentation_url
        else:
            logger.warning("Could not find presentation URL in output")
            logger.debug(f"Output: {result.stdout}")
            return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running md2gslides: {e}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Fix images and create Google Slides")
    parser.add_argument("markdown_file", help="Path to the markdown file")
    parser.add_argument("--expiry", choices=["1h", "12h", "24h", "72h"], default="24h",
                        help="Expiry time for uploaded images (default: 24h)")
    parser.add_argument("--title-prefix", default="", help="Prefix for presentation title")
    parser.add_argument("--no-fileio", action="store_true", help="Don't use file.io for image uploads")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Check if the markdown file exists
    if not os.path.exists(args.markdown_file):
        logger.error(f"Markdown file not found: {args.markdown_file}")
        sys.exit(1)
    
    # Process the markdown file
    processed_md = process_markdown(args.markdown_file, args.expiry)
    
    # Create the presentation
    url = run_md2gslides(processed_md, args.title_prefix, not args.no_fileio)
    
    if url:
        print(f"\n✅ Presentation created and available at: {url}\n")
        print(f"Remember that uploaded images will expire after {args.expiry}")
    else:
        print("\n⚠️ Presentation may have been created, but URL couldn't be retrieved")
        print("Check for URLs in the command output or in Google Drive\n")

if __name__ == "__main__":
    main()