#!/usr/bin/env python3
"""
Embedded Image Converter for MakeSlides

This script does direct image embedding for slides:

1. Finds all images in the images directory
2. Creates SVG versions of any PNG images if needed
3. Directly embeds SVG content in the markdown 
4. Processes the markdown with md2gslides

Usage: python embed_images.py slides_your_file.md
"""

import os
import sys
import re
import logging
import argparse
import subprocess
import base64
import tempfile
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("embed_images")

def read_file(file_path):
    """Read file contents."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path, content):
    """Write content to file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def read_image_binary(img_path):
    """Read an image file in binary mode."""
    with open(img_path, 'rb') as f:
        return f.read()

def png_to_svg(png_path):
    """Convert PNG to SVG using Inkscape or other tools if available."""
    svg_path = png_path.replace('.png', '.svg')
    
    # Check if SVG already exists
    if os.path.exists(svg_path):
        logger.info(f"SVG already exists: {svg_path}")
        return svg_path
    
    # Check if we can convert using Inkscape
    try:
        cmd = f'npx @mermaid-js/mermaid-cli -i "{png_path}" -o "{svg_path}"'
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Converted {png_path} to {svg_path}")
        return svg_path
    except Exception as e:
        logger.warning(f"Failed to convert PNG to SVG: {e}")
        return None

def find_diagrams(json_file, base_name):
    """Find diagrams related to a specific markdown file."""
    if not os.path.exists(json_file):
        logger.warning(f"JSON file not found: {json_file}")
        return []
    
    try:
        import json
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        diagrams = []
        
        # Handle different JSON structures
        slides = []
        if isinstance(data, dict) and "slides" in data:
            slides = data["slides"]
        elif isinstance(data, list):
            slides = data
        
        # Extract diagrams
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            
            slide_num = slide.get("slide_number", 0)
            
            # Check for diagram content
            if slide.get("diagram_type") and slide.get("diagram_content"):
                diagram_type = slide.get("diagram_type")
                diagrams.append({
                    "slide_number": slide_num,
                    "type": diagram_type,
                    "path": f"images/{base_name}_slide{slide_num}_{diagram_type}.svg"
                })
            
            # Check for image URLs
            if slide.get("image_url"):
                img_url = slide.get("image_url")
                if isinstance(img_url, str) and "images/" in img_url:
                    diagrams.append({
                        "slide_number": slide_num,
                        "type": "image",
                        "path": img_url
                    })
        
        return diagrams
    except Exception as e:
        logger.error(f"Error parsing JSON file: {e}")
        return []

def embed_svg_images(markdown_path):
    """Find and embed SVG images directly in markdown."""
    content = read_file(markdown_path)
    original_content = content
    
    # Extract base name for finding related JSON
    base_name = os.path.basename(markdown_path).replace('slides_', '').replace('.md', '')
    json_file = os.path.join(os.path.dirname(markdown_path), f"slides_{base_name}.json")
    
    # First look for any diagram info in JSON
    diagrams = find_diagrams(json_file, base_name)
    
    # Create the images directory if needed
    images_dir = os.path.join(os.path.dirname(markdown_path), "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # First - find all explicitly referenced images
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    explicit_images = re.findall(image_pattern, content)
    
    if not explicit_images and not diagrams:
        logger.info("No image references found and no diagrams in JSON")
        
        # Last resort: search for images in the images directory
        if os.path.exists(images_dir):
            for file in os.listdir(images_dir):
                if file.endswith('.svg') and base_name in file:
                    logger.info(f"Found potential related SVG: {file}")
                    # Check if file matches slide pattern
                    match = re.search(r'slide(\d+)', file)
                    if match:
                        slide_num = match.group(1)
                        logger.info(f"Found image for slide {slide_num}: {file}")
                        diagrams.append({
                            "slide_number": int(slide_num),
                            "type": "svg",
                            "path": f"images/{file}"
                        })
        
        if not diagrams:
            return markdown_path
    
    # Combined list of images to process
    all_images = []
    
    # Add explicitly referenced images
    for alt_text, img_path in explicit_images:
        all_images.append({
            "alt_text": alt_text,
            "path": img_path,
            "reference": f"![{alt_text}]({img_path})"
        })
    
    # Add diagrams from JSON
    for diagram in diagrams:
        slide_path = diagram["path"]
        if os.path.exists(slide_path):
            all_images.append({
                "alt_text": f"Slide {diagram['slide_number']} {diagram['type']}",
                "path": slide_path,
                "reference": None,  # Need to find where to insert this
                "slide_number": diagram["slide_number"]
            })
        elif os.path.exists(slide_path.replace('.svg', '.png')):
            # Try to convert PNG to SVG
            png_path = slide_path.replace('.svg', '.png')
            svg_path = png_to_svg(png_path)
            if svg_path:
                all_images.append({
                    "alt_text": f"Slide {diagram['slide_number']} {diagram['type']}",
                    "path": svg_path,
                    "reference": None,
                    "slide_number": diagram["slide_number"]
                })
    
    # Process each image
    for img in all_images:
        path = img["path"]
        
        # Skip remote URLs
        if path.startswith(('http://', 'https://')):
            logger.info(f"Skipping remote URL: {path}")
            continue
        
        # Handle paths relative to images directory
        if not os.path.exists(path) and not path.startswith('images/'):
            path = f"images/{path}"
            if not os.path.exists(path):
                logger.warning(f"Image not found: {path}")
                continue
        
        # Check if it's an SVG
        if path.lower().endswith('.svg'):
            try:
                svg_content = read_file(path)
                
                # Create the SVG block replacement
                svg_block = f"\n$$$ svg\n{svg_content}\n$$$\n"
                
                # If this is an explicit reference, replace it
                if img["reference"]:
                    content = content.replace(img["reference"], svg_block)
                else:
                    # This is from a diagram in JSON - find appropriate slide
                    slide_num = img.get("slide_number")
                    if slide_num:
                        # Find the slide header
                        slide_pattern = re.compile(r'---\s+\n\s*#\s+.*?\n\s*(?:.*?\n)*?\s*---\s*\n', re.DOTALL)
                        slides = list(slide_pattern.finditer(content))
                        
                        if 0 <= slide_num-1 < len(slides):
                            # Insert after this slide's content
                            slide_match = slides[slide_num-1]
                            insert_pos = slide_match.end()
                            content = content[:insert_pos] + svg_block + content[insert_pos:]
                            logger.info(f"Inserted SVG for slide {slide_num}")
                        else:
                            logger.warning(f"Couldn't find position for slide {slide_num}")
            except Exception as e:
                logger.error(f"Error processing SVG {path}: {e}")
        else:
            logger.warning(f"Skipping non-SVG image: {path}")
    
    # If we made changes, save the file
    if content != original_content:
        backup_path = f"{markdown_path}.original"
        write_file(backup_path, original_content)
        logger.info(f"Original saved to {backup_path}")
        
        write_file(markdown_path, content)
        logger.info(f"Updated {markdown_path} with embedded SVGs")
    
    return markdown_path

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
    parser = argparse.ArgumentParser(description="Embed images and create Google Slides")
    parser.add_argument("markdown_file", help="Path to the markdown file")
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
    processed_md = embed_svg_images(args.markdown_file)
    
    # Create the presentation
    url = run_md2gslides(processed_md, args.title_prefix, not args.no_fileio)
    
    if url:
        print(f"\n✅ Presentation created and available at: {url}\n")
        print("Note: SVG images have been directly embedded in the markdown")
    else:
        print("\n⚠️ Presentation may have been created, but URL couldn't be retrieved")
        print("Check for URLs in the command output or in Google Drive\n")

if __name__ == "__main__":
    main()