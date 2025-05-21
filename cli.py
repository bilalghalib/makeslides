import argparse
from pathlib import Path
from makeslides.slides.builder import build_slides

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="makeslides",
        description="Generate Google Slides from guide JSON/Markdown"
    )
    parser.add_argument("source", type=Path, help="Guide markdown or JSON file")
    parser.add_argument("-o", "--out", type=Path, help="Generated deck path")
    parser.add_argument("--image-style", choices=["inline", "left", "background"], default="inline")
    args = parser.parse_args()

    build_slides(
        source=args.source,
        out=args.out,
        image_style=args.image_style,
    )

if __name__ == "__main__":
    main()

