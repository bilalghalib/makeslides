#!/usr/bin/env python3
"""
Unified presentation export tool - supports multiple output formats.

Usage:
    python export_presentation.py slides.json --format pptx
    python export_presentation.py slides.json --format revealjs --theme sky
    python export_presentation.py slides.json --format all
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from makeslides.exporters import PPTXExporter, RevealJSExporter

logger = logging.getLogger(__name__)


def load_slides_json(json_path: Path) -> List[Dict[str, Any]]:
    """
    Load slides from JSON file.

    Args:
        json_path: Path to JSON file

    Returns:
        List of slide dictionaries
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'slides' in data:
            return data['slides']
        else:
            logger.error("Unexpected JSON structure")
            return []

    except Exception as e:
        logger.error(f"Failed to load JSON: {e}")
        return []


def export_pptx(slides: List[Dict[str, Any]], output_path: Path) -> bool:
    """Export to PowerPoint format."""
    try:
        logger.info("Exporting to PPTX format...")
        exporter = PPTXExporter(slides, output_path)
        result_path = exporter.export()
        logger.info(f"✅ PPTX exported to: {result_path}")
        return True
    except Exception as e:
        logger.error(f"❌ PPTX export failed: {e}")
        return False


def export_revealjs(slides: List[Dict[str, Any]], output_path: Path,
                   theme: str = "black", embed_images: bool = True) -> bool:
    """Export to reveal.js HTML format."""
    try:
        logger.info(f"Exporting to reveal.js format (theme: {theme})...")
        exporter = RevealJSExporter(slides, output_path, theme=theme, embed_images=embed_images)
        result_path = exporter.export()
        logger.info(f"✅ reveal.js exported to: {result_path}")
        logger.info(f"   Open in browser: file://{result_path.absolute()}")
        return True
    except Exception as e:
        logger.error(f"❌ reveal.js export failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Export presentations to multiple formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export to PowerPoint
  python export_presentation.py slides.json --format pptx

  # Export to reveal.js with custom theme
  python export_presentation.py slides.json --format revealjs --theme sky

  # Export to all formats
  python export_presentation.py slides.json --format all

  # Specify output filename
  python export_presentation.py slides.json --format pptx --output my_presentation.pptx

Available reveal.js themes:
  black, white, league, beige, sky, night, serif, simple, solarized, moon
        """
    )

    parser.add_argument('json_file', type=Path, help='Path to slides JSON file')
    parser.add_argument('--format', '-f', choices=['pptx', 'revealjs', 'all'], default='pptx',
                       help='Output format (default: pptx)')
    parser.add_argument('--output', '-o', type=Path, help='Output file path')
    parser.add_argument('--theme', '-t', default='black',
                       help='reveal.js theme (default: black)')
    parser.add_argument('--no-embed-images', action='store_true',
                       help='Don\'t embed images in reveal.js (faster, but requires internet)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Validate JSON file
    if not args.json_file.exists():
        logger.error(f"JSON file not found: {args.json_file}")
        sys.exit(1)

    # Load slides
    logger.info(f"Loading slides from: {args.json_file}")
    slides = load_slides_json(args.json_file)

    if not slides:
        logger.error("No slides found in JSON file")
        sys.exit(1)

    logger.info(f"Loaded {len(slides)} slides")

    # Determine base name for outputs
    base_name = args.json_file.stem.replace('slides_', '')

    # Export based on format
    success = True

    if args.format == 'pptx' or args.format == 'all':
        output_path = args.output if args.output else Path(f"{base_name}.pptx")
        if not export_pptx(slides, output_path):
            success = False

    if args.format == 'revealjs' or args.format == 'all':
        output_path = args.output if args.output and args.format != 'all' else Path(f"{base_name}_revealjs.html")
        embed_images = not args.no_embed_images

        if not export_revealjs(slides, output_path, theme=args.theme, embed_images=embed_images):
            success = False

    if success:
        logger.info("✅ All exports completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Some exports failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
