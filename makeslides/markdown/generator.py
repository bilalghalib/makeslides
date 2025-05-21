#!/usr/bin/env python3
"""Convert slides.json to md2gslides compatible markdown files.

This script converts JSON slide data to markdown format compatible with md2gslides,
allowing for generation of Google Slides presentations with proper layouts.
"""
from __future__ import annotations
import argparse, json, logging, os, sys, re
from pathlib import Path
from typing import Dict, List, Any, Optional

LOGGER = logging.getLogger("json_to_markdown")

# Map of slide layouts to md2gslides format templates
LAYOUT_TEMPLATES = {
    "TITLE": {
        "template": """# {title}

{subtitle}
""",
        "fields": ["title", "subtitle"]
    },
    "TITLE_SLIDE": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    "TITLE_AND_BODY": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    "TITLE_AND_TWO_COLUMNS": {
        "template": """# {title}

{left_column}

{{.column}}

{right_column}
""",
        "fields": ["title", "left_column", "right_column"]
    },
    "TWO_COLUMNS": {
        "template": """# {title}

{left_column}

{{.column}}

{right_column}
""",
        "fields": ["title", "left_column", "right_column"]
    },
    "MAIN_POINT": {
        "template": """# {title} {{.big}}
""",
        "fields": ["title"]
    },
    "SECTION_HEADER": {
        "template": """# {title} {{.section}}
""",
        "fields": ["title"]
    },
    "BIG_NUMBER": {
        "template": """# {title} {{.big}}

{content}
""",
        "fields": ["title", "content"]
    },
    "CAPTION": {
        "template": """# {title}

![]({image_url})
""",
        "fields": ["title", "image_url"]
    },
    "BLANK": {
        "template": """# {title}

![]({image_url}){{.background}}
""",
        "fields": ["title", "image_url"]
    },
    # Add mappings for custom layouts
    "title": {
        "template": """# {title} {{.big}}

{content}
""",
        "fields": ["title", "content"]
    },
    "section": {
        "template": """# {title} {{.section}}
""",
        "fields": ["title"]
    },
    "content": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    "columns": {
        "template": """# {title}

{left_column}

{{.column}}

{right_column}
""",
        "fields": ["title", "left_column", "right_column"]
    },
    "activity": {
        "template": """# {title} {{.big}}

{content}
""",
        "fields": ["title", "content"]
    },
    "main_point": {
        "template": """# {title} {{.big}}
""",
        "fields": ["title"]
    },
    "big_number": {
        "template": """# {title} {{.big}}

{content}
""",
        "fields": ["title", "content"]
    },
    "logistics": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    "break": {
        "template": """# {title}

![]({image_url})
""",
        "fields": ["title", "image_url"]
    },
    "closing": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    # Add mappings for day5 layouts
    "title-slide": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    "content-focused": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    "two-column": {
        "template": """# {title}

{left_column}

{{.column}}

{right_column}
""",
        "fields": ["title", "left_column", "right_column"]
    },
    "image-and-text": {
        "template": """# {title}

{content}

![]({image_url})
""",
        "fields": ["title", "content", "image_url"]
    },
    "diagram": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    "comparison": {
        "template": """# {title}

{left_column}

{{.column}}

{right_column}
""",
        "fields": ["title", "left_column", "right_column"]
    },
    "discussion": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    },
    "DEFAULT": {
        "template": """# {title}

{content}
""",
        "fields": ["title", "content"]
    }
}

def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert slides.json to md2gslides markdown")
    p.add_argument("json", help="slides.json file or directory of JSON files")
    p.add_argument("--output-dir", default=None, help="Output directory for markdown files")
    p.add_argument("--prefer-svg", action="store_true", help="Prefer SVG over PNG for diagrams")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--log-file", default=None)
    p.add_argument("--debug", action="store_true", help="Print additional debug info about layouts")
    p.add_argument("--force-layouts", action="store_true", help="Force strict layout adherence")
    return p.parse_args()

def setup_logging(level: str, log_file: str | None):
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", handlers=handlers)

def split_content_into_columns(content: str) -> tuple[str, str]:
    """Split content into two columns based on content length, pipe character, or bullet points."""
    if not content:
        return "", ""
    
    # Check if there's a pipe character separating the columns
    if "|" in content:
        parts = content.split("|", 1)
        return parts[0].strip(), parts[1].strip()
    
    # Check if there are bullet points
    if re.search(r'^\s*[-*]\s+', content, re.MULTILINE):
        lines = content.split('\n')
        bullet_indices = [i for i, line in enumerate(lines) if re.match(r'^\s*[-*]\s+', line)]
        
        if bullet_indices:
            # Find the middle bullet point
            midpoint_idx = len(bullet_indices) // 2
            midpoint = bullet_indices[midpoint_idx]
            
            # Split at this bullet point
            left_column = '\n'.join(lines[:midpoint])
            right_column = '\n'.join(lines[midpoint:])
            return left_column, right_column
    
    # Default to simple splitting
    lines = content.split('\n')
    midpoint = len(lines) // 2
    left_column = '\n'.join(lines[:midpoint])
    right_column = '\n'.join(lines[midpoint:])
    
    return left_column, right_column

def format_svg_block(svg_path: Path) -> str:
    """Format an SVG file as a markdown SVG block."""
    try:
        svg_content = svg_path.read_text(encoding='utf-8')
        return f"\n$$$ svg\n{svg_content}\n$$$\n"
    except Exception as e:
        LOGGER.warning(f"Failed to read SVG file {svg_path}: {e}")
        return f"![]({svg_path})"

def format_slide(slide: Dict[str, Any], prefer_svg: bool = False, debug: bool = False) -> str:
    """Format a single slide as markdown based on its layout."""
    # Extract slide data
    layout = slide.get("layout", "DEFAULT")
    
    if debug:
        LOGGER.debug(f"Processing slide {slide.get('slide_number', '?')} with layout: {layout}")
        LOGGER.debug(f"Available layouts: {list(LAYOUT_TEMPLATES.keys())}")
    
    # Get layout template
    template_info = LAYOUT_TEMPLATES.get(layout, LAYOUT_TEMPLATES["DEFAULT"])
    if layout not in LAYOUT_TEMPLATES:
        LOGGER.warning(f"Unknown layout '{layout}' for slide {slide.get('slide_number', '?')}, using default")
    
    template = template_info["template"]
    
    # Create content with proper line breaks for bullets and paragraphs
    content = slide.get("content", "")
    if content:
        # Ensure bullet points have proper formatting
        content = re.sub(r'^\s*[-*]\s+', '* ', content, flags=re.MULTILINE)
        # Make sure each bullet point is on its own line
        content = re.sub(r'(\* [^\n]+)(?=[\s]*\* )', r'\1\n', content)
        # Preserve paragraph breaks (double newlines)
        content = re.sub(r'\n\n+', '\n\n', content)
        # Add double line breaks after headings
        content = re.sub(r'(#+[^\n]+)\n', r'\1\n\n', content)
    
    # Handle diagram content - if there's a diagram, add it to the content
    diagram_type = slide.get("diagram_type")
    diagram_content = slide.get("diagram_content")
    
    # Add diagram image reference if there is one
    if slide.get("image_url") and "diagram" in slide.get("image_url", ""):
        slide_num = slide.get("slide_number", 0)
        base_filename = slide.get("image_url").split('/')[-1].split('_slide')[0]
        
        # Create image reference
        if prefer_svg:
            svg_path = f"images/{base_filename}_slide{slide_num}.svg"
            if Path(svg_path).exists():
                if debug:
                    LOGGER.debug(f"Using SVG diagram: {svg_path}")
                content += f"\n\n$$$ svg\n{Path(svg_path).read_text() if Path(svg_path).exists() else '<!-- SVG not found -->'}\n$$$\n"
            else:
                png_path = f"images/{base_filename}_slide{slide_num}.png"
                if debug:
                    LOGGER.debug(f"Using PNG diagram: {png_path}")
                content += f"\n\n![]({png_path})\n"
        else:
            png_path = f"images/{base_filename}_slide{slide_num}.png"
            if debug:
                LOGGER.debug(f"Using PNG diagram: {png_path}")
            content += f"\n\n![]({png_path})\n"
    
    # Fallback method: check for diagrams by slide number and diagram type
    elif slide.get("diagram_type"):
        slide_num = slide.get("slide_number", 0)
        diagram_type = slide.get("diagram_type")
        source_file = os.path.basename(os.getcwd())
        
        # Try different naming patterns
        for pattern in [
            f"images/{source_file}_slide{slide_num}_{diagram_type}.png",
            f"images/{source_file}_slide{slide_num}.png",
            f"images/test_fix_workflow_slide{slide_num}.png",
            f"images/test_fix_workflow_slide{slide_num}_{diagram_type}.png",
            f"images/slide{slide_num}.png",
            f"images/slide{slide_num}_{diagram_type}.png"
        ]:
            if Path(pattern).exists():
                if debug:
                    LOGGER.debug(f"Found diagram image using pattern: {pattern}")
                content += f"\n\n![]({pattern})\n"
                break
                
        # If we still haven't found a match, look for any diagram with this slide number
        if "![](images/" not in content:
            png_files = list(Path("images").glob(f"*slide{slide_num}*.png"))
            if png_files:
                png_path = str(png_files[0])
                if debug:
                    LOGGER.debug(f"Using found diagram: {png_path}")
                content += f"\n\n![]({png_path})\n"
    
    # Handle image URL
    image_url = slide.get("image_url", "")
    if image_url and not "diagram" in image_url:
        # Check if there's an SVG version of the image
        if prefer_svg and image_url.lower().endswith('.png'):
            svg_path = image_url[:-4] + '.svg'
            svg_path_obj = Path(svg_path)
            if svg_path_obj.exists():
                # Use SVG block instead of image reference
                image_block = format_svg_block(svg_path_obj)
            else:
                image_block = f"![]({image_url})"
        else:
            image_block = f"![]({image_url})"
    else:
        image_block = ""
    
    # Create data dict for template
    data = {
        "title": slide.get("title", ""),
        "subtitle": slide.get("subtitle", ""),
        "content": content,
        "image_url": image_url,
        "image_block": image_block
    }
    
    # For two column layouts, split content and handle images
    if layout in ["TITLE_AND_TWO_COLUMNS", "columns", "TWO_COLUMNS", "two-column", "comparison"]:
        left, right = split_content_into_columns(data["content"])
        data["left_column"] = left
        
        # If there's an image, use it for the right column
        if image_url and not "diagram" in image_url:
            if prefer_svg and image_url.lower().endswith('.png'):
                svg_path = image_url[:-4] + '.svg'
                svg_path_obj = Path(svg_path)
                if svg_path_obj.exists():
                    # Use SVG block instead of image reference
                    data["right_column"] = format_svg_block(svg_path_obj)
                else:
                    data["right_column"] = f"![]({image_url})"
            else:
                data["right_column"] = f"![]({image_url})"
        else:
            data["right_column"] = right
    
    # Add speaker notes if available
    notes = slide.get("facilitator_notes", "")
    notes_section = f"\n\n<!--\n{notes}\n-->" if notes else ""
    
    # Format markdown
    try:
        md = template.format(**{k: v for k, v in data.items() if k in template_info["fields"]})
        return f"---\n\n{md}{notes_section}\n"
    except KeyError as e:
        LOGGER.warning(f"Missing field {e} for layout {layout}, using default")
        return f"---\n\n# {data['title']}\n\n{data['content']}{notes_section}\n"

def extract_slides_from_json(json_data: Any) -> List[Dict[str, Any]]:
    """Extract slides array from JSON data, handling different formats."""
    if isinstance(json_data, list):
        # Already a list of slides
        return json_data
    elif isinstance(json_data, dict) and "slides" in json_data:
        # Object with a slides key
        return json_data["slides"]
    else:
        LOGGER.warning("Unknown JSON structure, attempting to find slides array")
        # Try to find any array in the JSON
        for key, value in json_data.items() if isinstance(json_data, dict) else []:
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                LOGGER.info(f"Found slides array under key '{key}'")
                return value
        
        raise ValueError("Could not find a slides array in the JSON data")

def convert_json_to_markdown(json_path: Path, output_dir: Optional[Path] = None, 
                           prefer_svg: bool = False, debug: bool = False) -> Path:
    """Convert a single JSON file to markdown."""
    LOGGER.info("Converting %s to markdown", json_path)
    
    # Load JSON data
    try:
        json_data = json.loads(json_path.read_text(encoding='utf-8'))
        slides = extract_slides_from_json(json_data)
    except json.JSONDecodeError as e:
        LOGGER.error("Invalid JSON in %s: %s", json_path, e)
        raise
    except ValueError as e:
        LOGGER.error("%s", e)
        raise
    
    if debug:
        LOGGER.debug(f"Found {len(slides)} slides")
        layouts = {}
        for slide in slides:
            layout = slide.get("layout", "DEFAULT")
            layouts[layout] = layouts.get(layout, 0) + 1
        LOGGER.debug(f"Layout distribution: {layouts}")
    
    # Create markdown
    md_content = []
    for i, slide in enumerate(slides):
        try:
            slide_md = format_slide(slide, prefer_svg, debug)
            md_content.append(slide_md)
        except Exception as e:
            LOGGER.error(f"Error formatting slide {i+1}: {e}")
            # Create simple fallback slide
            title = slide.get("title", f"Slide {i+1}")
            content = slide.get("content", "")
            md_content.append(f"---\n\n# {title}\n\n{content}\n")
    
    # Join with newlines
    markdown = "\n".join(md_content)
    
    # Determine output path
    if output_dir:
        output_path = output_dir / f"slides_{json_path.stem.replace('slides_', '')}.md"
    else:
        output_path = json_path.with_name(f"slides_{json_path.stem.replace('slides_', '')}.md")
    
    # Write markdown file
    output_path.write_text(markdown, encoding='utf-8')
    LOGGER.info("Wrote markdown to %s", output_path)
    
    return output_path

def process_directory(json_dir: Path, output_dir: Optional[Path] = None, 
                    prefer_svg: bool = False, debug: bool = False) -> List[Path]:
    """Process all JSON files in a directory."""
    LOGGER.info("Processing all JSON files in %s", json_dir)
    
    # Find all JSON files
    json_files = list(json_dir.glob("slides_*.json"))
    if not json_files:
        # Try without slides_ prefix
        json_files = list(json_dir.glob("*.json"))
        if not json_files:
            LOGGER.error("No slide JSON files found in %s", json_dir)
            return []
    
    LOGGER.info("Found %d JSON files to process", len(json_files))
    
    # Process each file
    results = []
    for json_path in json_files:
        try:
            md_path = convert_json_to_markdown(json_path, output_dir, prefer_svg, debug)
            results.append(md_path)
        except Exception as e:
            LOGGER.error("Failed to convert %s: %s", json_path, e, exc_info=True)
    
    return results

def main():
    args = cli()
    setup_logging(args.log_level, args.log_file)
    
    # Validate paths
    json_path = Path(args.json)
    if not json_path.exists():
        LOGGER.error("%s not found", json_path)
        sys.exit(1)
    
    # Determine output directory
    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process files
    try:
        if json_path.is_dir():
            md_files = process_directory(json_path, output_dir, args.prefer_svg, args.debug)
            if md_files:
                LOGGER.info("Converted %d JSON files to markdown", len(md_files))
            else:
                LOGGER.warning("No markdown files were generated")
                sys.exit(1)
        else:
            convert_json_to_markdown(json_path, output_dir, args.prefer_svg, args.debug)
    except Exception as e:
        LOGGER.error("Processing failed: %s", e, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()