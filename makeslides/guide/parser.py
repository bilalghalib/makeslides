#!/usr/bin/env python3
"""Convert a facilitator guide into slides.json using Claude 3.

Usage:
  python guide_to_json.py guide.md \
      --config config.yaml \
      --out slides.json \
      --log-level INFO \
      --log-file build.log
      
  # Process all markdown files in a folder:
  python guide_to_json.py guides/ \
      --config config.yaml \
      --log-level INFO \
      --log-file build.log
"""
from __future__ import annotations
import argparse, json, logging, os, sys, time, yaml, re
from pathlib import Path
from typing import List, Dict, Any
import anthropic

DEFAULT_OUT = "slides.json"
DEFAULT_CONFIG = "config.yaml"

LOGGER = logging.getLogger("guide_to_json")


def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LLM → JSON slide outline")
    p.add_argument("guide", help="Facilitator guide (Markdown/text) or directory of guides")
    p.add_argument("--config", default=DEFAULT_CONFIG, help="YAML config with prompt template and layout mappings")
    p.add_argument("--out", default=None, help="Output JSON path (ignored if guide is a directory)")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--log-file", default=None, help="Write logs to file as well")
    p.add_argument("--model", default="claude-3-7-sonnet-20250219", help="Claude model to use")
    p.add_argument("--batch-size", type=int, default=5, help="Number of files to process in parallel (batch mode)")
    p.add_argument("--force-json", action="store_true", help="Force JSON extraction even if response is not valid JSON")
    return p.parse_args()


def setup_logging(level: str, log_file: str | None):
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load YAML configuration file with prompt template and layout mappings."""
    if not config_path.exists():
        LOGGER.warning("Config file %s not found, using defaults", config_path)
        return {
            "prompt_template": "{{content}}",
            "layout_mappings": {},
            "slide_defaults": {}
        }
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Ensure required keys exist
    config.setdefault("prompt_template", "{{content}}")
    config.setdefault("layout_mappings", {})
    config.setdefault("slide_defaults", {})
    
    return config


def build_prompt(template: str, guide_text: str) -> str:
    """Insert guide text into prompt template."""
    if "{{content}}" not in template:
        LOGGER.error("Prompt template missing {{content}} placeholder")
        sys.exit(1)
    return template.replace("{{content}}", guide_text)


# Insert missing keys and correct ordering
ORDER = [
    "slide_number", "title", "content", "layout", "chart_type", "diagram_type", "diagram_content",
    "image_description", "image_url", "facilitator_notes", "start_time", "end_time",
    "materials", "worksheet", "improvements", "notes",
]


def normalize(slides: list[dict], layout_mappings: Dict[str, str], slide_defaults: Dict[str, Any]) -> list[dict]:
    """Normalize slides by adding missing keys and applying layout mappings."""
    fixed = []
    for idx, raw in enumerate(slides, 1):
        # Apply defaults
        for key, value in slide_defaults.items():
            raw.setdefault(key, value)
        
        # Set slide number
        raw.setdefault("slide_number", idx)
        
        # Apply layout mapping if available
        layout = raw.get("layout")
        if not layout:
            # Determine layout based on content
            if idx == 1:
                raw["layout"] = "TITLE"
            elif raw.get("image_url") or raw.get("diagram_type"):
                raw["layout"] = "TITLE_AND_TWO_COLUMNS"
            else:
                raw["layout"] = "TITLE_AND_BODY"
        
        # Apply custom layout mappings
        if layout in layout_mappings:
            raw["layout"] = layout_mappings[layout]
        
        # Ensure all other keys exist
        raw.setdefault("chart_type", None)
        raw.setdefault("image_description", None)
        raw.setdefault("image_url", None)
        for key in ORDER:
            raw.setdefault(key, None)
        
        # Create ordered dictionary
        fixed.append({k: raw.get(k) for k in ORDER})
    
    return fixed


def extract_json(text: str, force: bool = False) -> list:
    """Extract JSON array from text, even if surrounded by non-JSON content."""
    # Try to find a JSON array using regex
    array_match = re.search(r'(\[\s*{.*}\s*\])', text, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group(1))
        except json.JSONDecodeError:
            pass  # Fall through to other methods
    
    # Look for common JSON array start/end
    start_idx = text.find('[')
    end_idx = text.rfind(']')
    
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        try:
            return json.loads(text[start_idx:end_idx+1])
        except json.JSONDecodeError:
            pass  # Fall through to other methods
    
    # If force enabled, try to extract JSON objects and build an array
    if force:
        LOGGER.warning("Attempting to force JSON extraction from malformed response")
        objects = re.findall(r'{\s*"slide_number"\s*:.*?}', text, re.DOTALL)
        if objects:
            result = []
            for obj_str in objects:
                try:
                    # Replace any trailing commas that would make the JSON invalid
                    obj_str = re.sub(r',\s*}', '}', obj_str)
                    obj = json.loads(obj_str)
                    result.append(obj)
                except json.JSONDecodeError:
                    continue
            
            if result:
                LOGGER.info(f"Successfully extracted {len(result)} slide objects")
                return result
    
    raise json.JSONDecodeError("Could not extract valid JSON from response", text, 0)


def process_guide(guide_path: Path, config: Dict[str, Any], out_path: Path | None, model: str, client: anthropic.Anthropic, force_json: bool = False) -> Path:
    """Process a single guide file and return the output path."""
    LOGGER.info("Processing guide: %s", guide_path)
    
    # Determine output path
    if not out_path:
        out_path = guide_path.with_name(f"slides_{guide_path.stem}.json")
    
    # Read guide and build prompt
    guide_txt = guide_path.read_text(encoding="utf-8")
    prompt = build_prompt(config["prompt_template"], guide_txt)
    
    # Define tool for JSON extraction
    tools = [
        {
            "name": "generate_slides",
            "description": "Generate slides from facilitator guide",
            "input_schema": {
                "type": "object",
                "properties": {
                    "slides": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "slide_number": {"type": "integer"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "layout": {"type": "string"},
                                "chart_type": {"type": ["string", "null"]},
                                "diagram_type": {"type": ["string", "null"]},
                                "diagram_content": {"type": ["string", "null"]},
                                "image_description": {"type": ["string", "null"]},
                                "image_url": {"type": ["string", "null"]},
                                "facilitator_notes": {"type": ["string", "null"]},
                                "start_time": {"type": ["string", "null"]},
                                "end_time": {"type": ["string", "null"]},
                                "materials": {"type": ["string", "null"]},
                                "worksheet": {"type": ["string", "null"]},
                                "improvements": {"type": ["string", "null"]},
                                "notes": {"type": ["string", "null"]}
                            },
                            "required": ["slide_number", "title", "content", "layout"]
                        }
                    }
                },
                "required": ["slides"]
            }

        }
    ]
    
    # Request Claude with retries
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            LOGGER.info("Requesting Claude (%s) for %s...", model, guide_path.name)
            
            # Try with tools first
            try:
                rsp = client.messages.create(
                    model=model,
                    max_tokens=16_000,
                    system="You are an expert at converting facilitator guides into well-structured slide content. Return valid JSON only.",
                    messages=[{"role": "user", "content": prompt}],
                    tools=tools
                )
                
                # Extract JSON from tool use
                slides = None
                for content in rsp.content:
                    if hasattr(content, 'type') and content.type == "tool_use" and content.name == "generate_slides":
                        slides = content.input["slides"]
                        break
                
                if slides:
                    # Normalize and save
                    slides = normalize(slides, config["layout_mappings"], config["slide_defaults"])
                    out_path.write_text(json.dumps(slides, indent=2, ensure_ascii=False))
                    LOGGER.info("Wrote %d slides → %s", len(slides), out_path)
                    return out_path
            except Exception as e:
                LOGGER.warning("Tool-based approach failed: %s. Falling back to text extraction.", e)
            
            # Fallback to traditional approach
            rsp = client.messages.create(
                model=model,
                max_tokens=16_000,
                system="Return JSON only. Your response should be a valid JSON array of slide objects, each with slide_number, title, content, and other fields.",
                messages=[{"role": "user", "content": prompt}],
            )
            
            raw = rsp.content[0].text
            
            # Try to extract JSON from the response
            try:
                slides = extract_json(raw, force_json)
            except json.JSONDecodeError as e:
                if attempt < max_attempts - 1:
                    LOGGER.warning("Invalid JSON from Claude: %s, retrying in %d seconds...", e, 2 ** attempt)
                    time.sleep(2 ** attempt)
                    continue
                else:
                    LOGGER.error("Invalid JSON from Claude after %d attempts: %s", max_attempts, e)
                    
                    # Debug: Save the raw response to a file for inspection
                    debug_path = out_path.with_suffix(".debug.txt")
                    debug_path.write_text(raw)
                    LOGGER.error(f"Saved raw response to {debug_path} for debugging")
                    
                    raise
            
            # Normalize and save
            slides = normalize(slides, config["layout_mappings"], config["slide_defaults"])
            out_path.write_text(json.dumps(slides, indent=2, ensure_ascii=False))
            LOGGER.info("Wrote %d slides → %s", len(slides), out_path)
            return out_path
            
        except (anthropic.APIError, anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
            if attempt < max_attempts - 1:
                LOGGER.warning("API error (attempt %d/%d): %s. Retrying in %d seconds...", 
                            attempt + 1, max_attempts, e, 2 ** attempt)
                time.sleep(2 ** attempt)
            else:
                LOGGER.error("API error after %d attempts: %s", max_attempts, e, exc_info=True)
                raise
    
    raise RuntimeError("Failed to process guide, this should not happen")  # Unreachable


def process_directory(guide_dir: Path, config: Dict[str, Any], model: str, batch_size: int, client: anthropic.Anthropic, force_json: bool = False) -> List[Path]:
    """Process all markdown files in a directory."""
    LOGGER.info("Processing all markdown files in: %s", guide_dir)
    
    # Find all markdown and text files
    md_files = list(guide_dir.glob("*.md")) + list(guide_dir.glob("*.txt"))
    if not md_files:
        LOGGER.error("No markdown or text files found in %s", guide_dir)
        sys.exit(1)
    
    LOGGER.info("Found %d files to process", len(md_files))
    
    # Process files in batches to avoid overwhelming the API
    results = []
    for i in range(0, len(md_files), batch_size):
        batch = md_files[i:i + batch_size]
        LOGGER.info("Processing batch %d/%d (%d files)", i // batch_size + 1, 
                   (len(md_files) + batch_size - 1) // batch_size, len(batch))
        
        for guide_path in batch:
            try:
                out_path = process_guide(guide_path, config, None, model, client, force_json)
                results.append(out_path)
            except Exception as e:
                LOGGER.error("Failed to process %s: %s", guide_path, e, exc_info=True)
    
    return results


def main():
    args = cli()
    setup_logging(args.log_level, args.log_file)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        LOGGER.error("Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    # Load configuration
    config_path = Path(args.config)
    config = load_config(config_path)
    
    # Validate paths
    guide_path = Path(args.guide)
    
    if not guide_path.exists():
        LOGGER.error("Guide path not found: %s", guide_path)
        sys.exit(1)
    
    # Initialize Claude client
    client = anthropic.Anthropic(api_key=api_key)
    
    if guide_path.is_dir():
        LOGGER.info("Directory mode: Processing all markdown files in %s", guide_path)
        if args.out:
            LOGGER.warning("--out parameter ignored in directory mode")
        
        # Process directory
        process_directory(guide_path, config, args.model, args.batch_size, client, args.force_json)
        
    else:
        # Single file mode
        # Determine output path
        out_path = Path(args.out) if args.out else guide_path.with_name(f"slides_{guide_path.stem}.json")
        
        # Process single guide
        process_guide(guide_path, config, out_path, args.model, client, args.force_json)


if __name__ == "__main__":
    main()