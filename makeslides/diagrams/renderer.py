#!/usr/bin/env python3
"""
Render Mermaid diagrams to local image files with improved reliability.

This script finds diagram definitions in the JSON slides data, renders them
to local image files, and updates the JSON with the image paths.

The improved version offers:
1. Better path handling with consistent naming patterns
2. More robust error recovery and fallbacks
3. Validation of diagram content before rendering
4. Multiple retries with different approaches
5. Detailed logging for troubleshooting

Usage: python diagrams_to_images.py slides_your_file.json
"""

import os
import sys
import subprocess
import json
import logging
import argparse
import time
import hashlib
import re
import tempfile
from pathlib import Path
import anthropic

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("diagrams_to_images")

# Default Mermaid CLI command
MERMAID_CMD = "mmdc"

# Common diagram type mappings for fallbacks
DIAGRAM_FALLBACKS = {
    "flowchart": ["flowchart TD", "flowchart LR", "flowchart RL", "mindmap"],
    "mindmap": ["mindmap", "flowchart TD", "flowchart LR"],
    "pie": ["pie", "flowchart TD"],
    "quadrantChart": ["quadrantChart", "flowchart"],
    "classDiagram": ["classDiagram", "flowchart TD"],
    "timeline": ["timeline", "flowchart TD"]
}

def validate_paths(json_path, output_dir=None, config_path=None):
    """Validate and normalize all paths, creating directories if needed."""
    # Check JSON file
    if not os.path.exists(json_path):
        logger.error(f"JSON file not found: {json_path}")
        return None, None, None
    
    # Determine output directory
    if output_dir:
        output_dir = os.path.abspath(output_dir)
    else:
        output_dir = os.path.join(os.path.dirname(json_path), "images")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Check Mermaid config
    if config_path and not os.path.exists(config_path):
        logger.warning(f"Mermaid config file not found: {config_path}, using default")
        config_path = None
    
    # Determine source file name for diagram naming conventions
    json_name = os.path.basename(json_path)
    source_name = json_name.replace("slides_", "").replace(".json", "")
    
    return json_path, output_dir, config_path, source_name

def load_json_content(json_path):
    """Load JSON content with improved error handling."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_content = f.read()
        
        try:
            data = json.loads(json_content)
            
            # Check if it's an object with a slides array
            if isinstance(data, dict) and "slides" in data:
                return data, data["slides"]
            elif isinstance(data, list):
                return {"slides": data}, data
            else:
                logger.error("Unexpected JSON structure: expected slides array or object with slides key")
                return None, None
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {json_path}: {e}")
            return None, None
            
    except Exception as e:
        logger.error(f"Failed to read {json_path}: {e}")
        return None, None

def is_valid_mermaid_syntax(src):
    """Check if the diagram content has valid Mermaid syntax structure."""
    # Valid Mermaid diagrams usually start with a diagram type followed by direction
    # e.g., "flowchart TD", "mindmap", "classDiagram", etc.
    pattern = r'^(flowchart|mindmap|classDiagram|pie|quadrantChart|timeline|sequenceDiagram|stateDiagram-v2|gantt|journey|gitGraph)\s*([A-Z]{2})?'
    if re.match(pattern, src.strip()):
        return True
    
    # Check if it contains any Mermaid-specific syntax
    mermaid_syntax = ['-->', '-.->', '===>', '-->|', '-.->|', '==>|', '---|', '-.-|', '===|']
    return any(token in src for token in mermaid_syntax)

def fix_mermaid_syntax(src, diagram_type):
    """Fix common syntax issues in Mermaid diagrams."""
    # If empty or None, create a minimal diagram
    if not src or src.strip() == "":
        if diagram_type.lower() == "flowchart":
            return "flowchart TD\n    A[Start] --> B[Process]"
        elif diagram_type.lower() == "mindmap":
            return "mindmap\n    root(Main Topic)"
        else:
            return f"{diagram_type}\n    A[Item 1]"
    
    # Ensure proper diagram type prefix
    if diagram_type.lower() == "flowchart" and not src.strip().lower().startswith("flowchart"):
        # If it's missing the diagram type, add it
        return f"flowchart TD\n{src}"
    
    # For other diagram types, check if the correct prefix is present
    if not src.strip().lower().startswith(diagram_type.lower()):
        return f"{diagram_type}\n{src}"
    
    return src

def fix_mermaid_with_claude(src, error_msg, client, model):
    """Use Claude to fix Mermaid syntax errors."""
    if not client:
        return src
        
    prompt = f"""You are a Mermaid diagram expert. Fix the following Mermaid diagram that has syntax errors.

Error message:
{error_msg}

Current diagram:
{src}

Please provide ONLY the fixed diagram code with no explanation or markdown formatting - just return the raw fixed Mermaid syntax.
Follow these guidelines:
- Ensure proper spacing in syntax (e.g., "A --> B")
- No extra spaces inside node brackets (use "[Label]", not "[ Label ]")
- Use capital letters for directions (TD, LR, BT, RL)
- Keep diagrams simple with 15 or fewer nodes
- Start with diagram type and direction (e.g., "flowchart TD")
- ONLY use standard Mermaid types: flowchart, mindmap, pie, classDiagram, etc.
- Do NOT create custom types like "illustration" or non-standard formats
"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0.0,
            system="You are a diagram syntax expert who returns only fixed mermaid syntax - no explanations.",
            messages=[{"role": "user", "content": prompt}]
        )
        fixed_src = response.content[0].text.strip()
        
        # Check if the response includes markdown formatting and remove it
        if fixed_src.startswith("```") and fixed_src.endswith("```"):
            fixed_src = fixed_src[3:-3].strip()
            if fixed_src.startswith("mermaid\n"):
                fixed_src = fixed_src[8:].strip()
        
        logger.info("Claude fixed the Mermaid syntax issues")
        return fixed_src
    except Exception as e:
        logger.error(f"Error using Claude to fix Mermaid: {e}")
        return src  # Return original if Claude fails

def render_mermaid(src, output_dir, config_path, base_filename, slide_num, diagram_type, client=None, model=""):
    """Render a Mermaid diagram to image files with comprehensive error handling."""
    # Create content hash for uniqueness
    content_hash = hashlib.md5(src.encode()).hexdigest()[:8]
    
    # Create filenames with consistent naming pattern
    diagram_type_slug = diagram_type.lower().replace(' ', '_')
    output_name = f"{base_filename}_slide{slide_num}_{diagram_type_slug}"
    
    mmd = os.path.join(output_dir, f"{output_name}.mmd")
    png = os.path.join(output_dir, f"{output_name}.png")
    svg = os.path.join(output_dir, f"{output_name}.svg")
    
    # Check if files already exist - if so, return them directly
    if os.path.exists(png) and os.path.stat(png).st_size > 0:
        logger.info(f"Diagram files already exist for slide {slide_num}, reusing them")
        return png
    
    # Validate and fix Mermaid syntax
    if not is_valid_mermaid_syntax(src):
        logger.warning(f"Slide {slide_num}: Invalid Mermaid syntax. Attempting to fix...")
        src = fix_mermaid_syntax(src, diagram_type)
    
    # Write Mermaid content to file
    try:
        with open(mmd, 'w', encoding='utf-8') as f:
            f.write(src)
    except Exception as e:
        logger.error(f"Error writing Mermaid file: {e}")
        return None
    
    # Build command with optional config
    cmd = [MERMAID_CMD, "-i", mmd, "-o", png]
    if config_path and os.path.exists(config_path):
        cmd.extend(["-c", config_path])
    
    # Also generate SVG with another command
    svg_cmd = [MERMAID_CMD, "-i", mmd, "-o", svg]
    if config_path and os.path.exists(config_path):
        svg_cmd.extend(["-c", config_path])
    
    # Execute command with retry and fallback mechanisms
    for attempt in range(3):
        try:
            # If it's not the first attempt, try fixing the diagram
            if attempt > 0:
                if attempt == 1 and client:
                    # Use Claude to fix syntax
                    new_src = fix_mermaid_with_claude(src, last_error, client, model)
                    if new_src != src:
                        src = new_src
                        with open(mmd, 'w', encoding='utf-8') as f:
                            f.write(src)
                elif attempt == 2:
                    # Try with a fallback diagram type
                    fallback_types = DIAGRAM_FALLBACKS.get(diagram_type.lower(), [])
                    if fallback_types:
                        fallback = fallback_types[0]
                        logger.info(f"Trying fallback diagram type: {fallback}")
                        
                        # Create a simplified diagram with the fallback type
                        fallback_src = f"{fallback}\n    A[Start] --> B[End]"
                        
                        with open(mmd, 'w', encoding='utf-8') as f:
                            f.write(fallback_src)
            
            logger.info(f"Rendering diagram for slide {slide_num} (attempt {attempt+1}/3)")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Check if PNG was generated successfully
            if os.path.exists(png) and os.path.stat(png).st_size > 0:
                # Also try generating SVG
                try:
                    subprocess.run(svg_cmd, check=True, capture_output=True, text=True)
                except Exception as e:
                    logger.warning(f"SVG generation failed but PNG succeeded: {e}")
                
                logger.info(f"Successfully rendered diagram for slide {slide_num}")
                return png
            else:
                logger.warning(f"Empty PNG generated for slide {slide_num}")
                last_error = "Empty output file"
                time.sleep(1)
                
        except subprocess.CalledProcessError as e:
            last_error = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            logger.warning(f"Mermaid CLI error (attempt {attempt+1}/3): {last_error}")
            time.sleep(2)  # Wait before retrying
    
    # All attempts failed - create a fallback image with error message
    logger.error(f"Failed to render Mermaid diagram after 3 attempts for slide {slide_num}")
    
    try:
        # Create a simple text file for identification
        with open(f"{png}.error", 'w', encoding='utf-8') as f:
            f.write(f"Failed to render diagram for slide {slide_num}\n")
            f.write(f"Original diagram type: {diagram_type}\n")
            f.write(f"Error: {last_error}\n")
        
        # Try to create a basic fallback image if possible
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a blank image
            img = Image.new('RGB', (800, 400), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            
            # Try to use a default font
            try:
                font = ImageFont.truetype("Arial", 20)
            except IOError:
                font = ImageFont.load_default()
            
            # Add error text
            d.text((50, 50), f"Failed to render diagram for slide {slide_num}", fill=(0, 0, 0), font=font)
            d.text((50, 100), f"Original diagram type: {diagram_type}", fill=(0, 0, 0), font=font)
            d.text((50, 150), "Please simplify or check syntax", fill=(0, 0, 0), font=font)
            
            # Save the image
            img.save(png)
            logger.info(f"Created fallback image for slide {slide_num}")
            return png
            
        except ImportError:
            # If PIL is not available, create a minimal PNG
            with open(png, 'wb') as f:
                # Minimal transparent PNG
                f.write(bytes.fromhex(
                    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
                    "890000000d4944415478da6364f8ffbf0600050001e36172eb0000000049454e44ae426082"
                ))
            logger.info(f"Created minimal fallback image for slide {slide_num}")
            return png
    except Exception as e:
        logger.error(f"Failed to create fallback image: {e}")
        
        # If absolutely everything fails, return None
        return None

def process_slides(slides, output_dir, config_path, source_name, client, model):
    """Process all slides to find and render diagrams."""
    changes = 0
    processed_hashes = {}  # Track already processed diagrams to avoid duplicates
    
    for slide in slides:
        if not isinstance(slide, dict):
            continue
            
        slide_num = slide.get("slide_number", 0)
        
        # Process diagrams
        if slide.get("diagram_type") and slide.get("diagram_content"):
            try:
                diagram_type = slide.get("diagram_type")
                diagram_content = slide.get("diagram_content")
                
                # Skip if this is null content
                if not diagram_content or diagram_content == "null":
                    continue
                    
                # Skip if we've already processed this exact content
                content_hash = hashlib.md5(diagram_content.encode()).hexdigest()
                if content_hash in processed_hashes:
                    slide["image_url"] = processed_hashes[content_hash]
                    changes += 1
                    logger.info(f"Slide {slide_num}: Reusing previously generated diagram")
                    continue
                
                # Render the diagram
                logger.info(f"Processing diagram for slide {slide_num} ({diagram_type})")
                img_path = render_mermaid(
                    diagram_content, 
                    output_dir, 
                    config_path, 
                    source_name, 
                    slide_num,
                    diagram_type,
                    client,
                    model
                )
                
                if img_path:
                    # Update the slide with the image path
                    rel_path = os.path.relpath(img_path, os.path.dirname(output_dir))
                    slide["image_url"] = rel_path
                    processed_hashes[content_hash] = rel_path
                    changes += 1
                    logger.info(f"Slide {slide_num}: Added image path {rel_path}")
                else:
                    logger.error(f"Slide {slide_num}: Failed to generate diagram")
                    
            except Exception as e:
                logger.error(f"Error processing diagram for slide {slide_num}: {e}")
    
    return changes

def save_updated_json(json_path, data, changes):
    """Save the updated JSON data back to file."""
    if changes > 0:
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Updated JSON file with {changes} changes: {json_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save updated JSON: {e}")
            return False
    else:
        logger.info("No changes to save")
        return True

def process_json_file(json_path, output_dir, config_path, client, model):
    """Process a single JSON file and render all diagrams."""
    # Validate and normalize paths
    json_path, output_dir, config_path, source_name = validate_paths(json_path, output_dir, config_path)
    if not json_path:
        return False
        
    # Load JSON data
    data, slides = load_json_content(json_path)
    if not slides:
        return False
        
    # Process all slides and render diagrams
    changes = process_slides(slides, output_dir, config_path, source_name, client, model)
    
    # Save updated JSON
    return save_updated_json(json_path, data, changes)

def process_directory(dir_path, output_dir, config_path, client, model):
    """Process all JSON files in a directory."""
    # Find all JSON files
    json_files = [f for f in os.listdir(dir_path) if f.endswith('.json')]
    if not json_files:
        logger.error(f"No JSON files found in {dir_path}")
        return False
        
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    success = True
    for json_file in json_files:
        json_path = os.path.join(dir_path, json_file)
        
        # Create subdirectory for each file if needed
        if output_dir:
            file_output_dir = output_dir
        else:
            file_output_dir = os.path.join(dir_path, "images")
            
        # Process the file
        file_success = process_json_file(json_path, file_output_dir, config_path, client, model)
        if not file_success:
            success = False
            
    return success

def initialize_claude_client():
    """Initialize the Claude client for syntax fixing if API key is available."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            logger.info("Initialized Claude client for diagram fixing")
            return client
        except Exception as e:
            logger.warning(f"Failed to initialize Claude client: {e}")
            return None
    else:
        logger.warning("ANTHROPIC_API_KEY not set, Claude-assisted fixing unavailable")
        return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Render Mermaid diagrams from JSON")
    parser.add_argument("json", help="slides.json file or directory of JSON files")
    parser.add_argument("--output-dir", help="Directory to save image files")
    parser.add_argument("--mermaid-config", default="mermaid-config.json", help="Mermaid configuration file")
    parser.add_argument("--model", default="claude-3-7-sonnet-20250219", help="Claude model to use for fixing diagrams")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--check-cmd", action="store_true", help="Check if Mermaid CLI is installed")
    
    args = parser.parse_args()
    
    # Configure logging
    logger.setLevel(getattr(logging, args.log_level))
    
    # Check if Mermaid CLI is installed
    if args.check_cmd:
        try:
            subprocess.run([MERMAID_CMD, "--version"], check=True, capture_output=True)
            logger.info("Mermaid CLI (mmdc) is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Mermaid CLI (mmdc) is not installed or not in PATH")
            logger.info("Install with: npm install -g @mermaid-js/mermaid-cli")
            sys.exit(1)
    
    # Initialize Claude client if API key is available
    client = initialize_claude_client()
    
    # Process files
    input_path = args.json
    if os.path.isdir(input_path):
        success = process_directory(input_path, args.output_dir, args.mermaid_config, client, args.model)
    else:
        success = process_json_file(input_path, args.output_dir, args.mermaid_config, client, args.model)
        
    if success:
        logger.info("✅ Successfully processed all diagrams")
        sys.exit(0)
    else:
        logger.error("❌ Failed to process some diagrams")
        sys.exit(1)

if __name__ == "__main__":
    main()