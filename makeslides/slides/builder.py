#!/usr/bin/env python3
"""Create Google Slides from markdown using md2gslides.

This script takes markdown files generated from JSON slides data and
uses the md2gslides npm package to create Google Slides presentations.
"""
from __future__ import annotations
import argparse, json, logging, os, sys, subprocess, tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import re
import shutil

LOGGER = logging.getLogger("build_with_md2gslides")

def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Google Slides from markdown")
    p.add_argument("markdown", help="Markdown file or directory of markdown files")
    p.add_argument("--title-prefix", default="", help="Prefix for presentation titles")
    p.add_argument("--style", default="github", help="Syntax highlighting style")
    p.add_argument("--use-fileio", action="store_true", help="Allow uploading to file.io for images")
    p.add_argument("--output-file", default=None, help="File to save presentation URLs")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--log-file", default=None)
    p.add_argument("--debug", action="store_true", help="Show debug info and display markdown before sending")
    p.add_argument("--append", default=None, help="Append to existing presentation ID")
    p.add_argument("--erase", action="store_true", help="Erase existing slides when using --append")
    p.add_argument("--verify-npm", action="store_true", help="Verify npm and md2gslides are installed")
    p.add_argument("--fix-format", action="store_true", help="Fix common markdown formatting issues")
    return p.parse_args()


def setup_logging(level: str, log_file: str | None):
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", handlers=handlers)


def verify_installation() -> bool:
    """Verify that npm and md2gslides are installed."""
    try:
        npm_version = subprocess.run(["npm", "--version"], capture_output=True, check=True, text=True)
        LOGGER.info(f"npm version: {npm_version.stdout.strip()}")
        
        # Try to install md2gslides if not already installed
        try:
            result = subprocess.run(["md2gslides", "--version"], capture_output=True, text=True)
            LOGGER.info(f"md2gslides version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            LOGGER.warning("md2gslides not found, attempting to install it...")
            try:
                install_result = subprocess.run(["npm", "install", "-g", "md2gslides"], 
                                               capture_output=True, check=True, text=True)
                LOGGER.info("md2gslides installed successfully")
            except subprocess.CalledProcessError as e:
                LOGGER.error(f"Failed to install md2gslides: {e.stderr}")
                return False
        
        # Check for client_id.json
        home_dir = Path.home()
        client_id_path = home_dir / ".md2googleslides" / "client_id.json"
        if not client_id_path.exists():
            LOGGER.warning("client_id.json not found at ~/.md2googleslides/client_id.json")
            LOGGER.warning("You may need to set up Google API credentials.")
            LOGGER.warning("See: https://github.com/googleworkspace/md2googleslides#installation-and-usage")
            
            # Create the directory if it doesn't exist
            client_id_dir = client_id_path.parent
            client_id_dir.mkdir(parents=True, exist_ok=True)
            
            LOGGER.warning(f"Directory created at {client_id_dir}")
            LOGGER.warning("Please follow these steps to set up Google API credentials:")
            LOGGER.warning("1. Go to https://console.developers.google.com")
            LOGGER.warning("2. Create a new project or select an existing one")
            LOGGER.warning("3. Enable the Google Slides API in the API Library")
            LOGGER.warning("4. Go to Credentials page and click '+ Create credentials'")
            LOGGER.warning("5. Select 'OAuth client ID' and 'Desktop Application'")
            LOGGER.warning(f"6. Download the JSON file and save it as 'client_id.json' in {client_id_dir}")
        
        return True
    
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"Error checking installation: {e}")
        return False
    
    except FileNotFoundError:
        LOGGER.error("npm not found. Please install Node.js and npm first.")
        return False


def fix_markdown_format(content: str) -> str:
    """Fix common markdown formatting issues that cause md2gslides to fail."""
    # Ensure proper slide separators
    if "---" not in content:
        LOGGER.info("Adding slide separators to markdown")
        lines = content.split("\n")
        fixed_lines = []
        
        # Add separator before each heading if missing
        in_first_slide = True
        for i, line in enumerate(lines):
            if line.startswith("#") and not in_first_slide:
                if i > 0 and not lines[i-1].startswith("---"):
                    fixed_lines.append("---")
            elif line.startswith("#"):
                in_first_slide = False
                
            fixed_lines.append(line)
        
        content = "\n".join(fixed_lines)
    
    # Ensure each slide has a title (header)
    sections = content.split("---")
    fixed_sections = []
    
    for i, section in enumerate(sections):
        section = section.strip()
        if section and not re.search(r'^#\s+.+', section, re.MULTILINE):
            LOGGER.info(f"Adding missing header to slide {i+1}")
            section = f"# Slide {i+1}\n\n{section}"
        
        fixed_sections.append(section)
    
    fixed_content = "---\n\n".join(fixed_sections)
    if not fixed_content.startswith("---"):
        fixed_content = fixed_content.lstrip("---").strip()
    
    # Fix image paths
    # Just a placeholder, add specific image path fixing if needed
    
    return fixed_content


def validate_markdown(markdown_path: Path, debug: bool = False, fix_format: bool = False) -> bool:
    """Validate markdown file for compatibility with md2gslides."""
    try:
        content = markdown_path.read_text(encoding="utf-8")
        
        # Check for common issues
        if not content.strip():
            LOGGER.error(f"{markdown_path} is empty")
            return False
        
        needs_fixing = False
        
        # Check for slide separators
        if "---" not in content and content.strip().count("\n") > 5:
            LOGGER.warning(f"{markdown_path} is missing slide separators (---)")
            needs_fixing = True
        
        # Check for headers
        if not re.search(r'^#\s+.+', content, re.MULTILINE):
            LOGGER.warning(f"{markdown_path} is missing slide headers (# Title)")
            needs_fixing = True
        
        # Check for image paths
        image_paths = re.findall(r'!\[.*?\]\((.*?)\)', content)
        for path in image_paths:
            if path.startswith("http"):
                continue
                
            img_path = Path(path)
            if not img_path.is_absolute():
                # Try relative to the markdown file
                img_path = markdown_path.parent / img_path
                
            if not img_path.exists():
                LOGGER.warning(f"Image path may be invalid: {path}")
        
        # Fix markdown if requested and needed
        if fix_format and needs_fixing:
            LOGGER.info(f"Fixing markdown format for {markdown_path}")
            fixed_content = fix_markdown_format(content)
            
            # Create backup of original file
            backup_path = markdown_path.with_suffix(".md.bak")
            shutil.copy2(markdown_path, backup_path)
            LOGGER.info(f"Created backup of original markdown at {backup_path}")
            
            # Write fixed content
            markdown_path.write_text(fixed_content, encoding="utf-8")
            content = fixed_content
            LOGGER.info(f"Fixed markdown formatting in {markdown_path}")
        
        if debug:
            LOGGER.info(f"\n---- Markdown Content ----\n{content}\n-------------------------")
            # Don't prompt for input to allow for automation
            LOGGER.info("Continuing with md2gslides automatically...")
        
        return True
        
    except Exception as e:
        LOGGER.error(f"Error validating markdown {markdown_path}: {e}")
        return False


def run_md2gslides(markdown_path: Path, title_prefix: str = "", style: str = "github", 
                 use_fileio: bool = False, append_id: Optional[str] = None, 
                 erase: bool = False, debug: bool = False) -> Optional[str]:
    """Run md2gslides to create a Google Slides presentation."""
    
    # Validate the markdown
    if not validate_markdown(markdown_path, debug):
        return None
    
    # Build the command
    cmd = ["md2gslides"]
    
    # Ensure md2gslides command exists
    try:
        # Check if md2gslides is in PATH
        md2gslides_path = shutil.which("md2gslides")
        if md2gslides_path:
            cmd = [md2gslides_path]
        else:
            # Try global npm installation
            cmd = ["npx", "md2gslides"]
    except Exception as e:
        LOGGER.error(f"Error finding md2gslides command: {e}")
        return None
    
    # Add the title
    title = f"{title_prefix}{markdown_path.stem}"
    cmd.extend(["--title", title])
    
    # Add optional arguments
    if style:
        cmd.extend(["--style", style])
    
    if use_fileio:
        cmd.append("--use-fileio")
    
    if append_id:
        cmd.extend(["--append", append_id])
        
        if erase:
            cmd.append("--erase")
    
    # Add the markdown file
    cmd.append(str(markdown_path))
    
    # Run the command
    LOGGER.info(f"Running command: {' '.join(cmd)}")
    try:
        # Create a temporary file to capture the output
        with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False) as tmp:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output to get the URL
            for line in result.stdout.splitlines():
                if "https://docs.google.com/presentation" in line:
                    url = line.strip()
                    LOGGER.info(f"Created presentation: {url}")
                    return url
            
            # If we can't find a URL, write the output to a file and return None
            tmp.write(result.stdout)
            LOGGER.warning(f"Could not find presentation URL in output. Output saved to {tmp.name}")
            if debug:
                LOGGER.info(f"Output:\n{result.stdout}")
            
            return None
        
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"Error running md2gslides: {e}")
        LOGGER.error(f"stdout: {e.stdout}")
        LOGGER.error(f"stderr: {e.stderr}")
        
        # Try to extract useful error messages
        error_lines = e.stderr.splitlines()
        for line in error_lines:
            if "Error:" in line or "TypeError:" in line or "SyntaxError:" in line:
                LOGGER.error(f"Error message: {line}")
        
        return None


def process_markdown_file(markdown_path: Path, title_prefix: str = "", style: str = "github", 
                       use_fileio: bool = False, output_file: Optional[Path] = None,
                       append_id: Optional[str] = None, erase: bool = False,
                       debug: bool = False, fix_format: bool = False) -> Optional[str]:
    """Process a single markdown file."""
    LOGGER.info(f"Processing markdown file: {markdown_path}")
    
    # Validate and potentially fix the markdown
    if not validate_markdown(markdown_path, debug, fix_format):
        LOGGER.error(f"Markdown validation failed for {markdown_path}")
        return None
    
    # Run md2gslides
    url = run_md2gslides(markdown_path, title_prefix, style, use_fileio, append_id, erase, debug)
    
    # Save the URL to the output file
    if url and output_file:
        try:
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(f"{markdown_path.stem}: {url}\n")
        except Exception as e:
            LOGGER.error(f"Error writing to output file {output_file}: {e}")
    
    return url


def process_directory(markdown_dir: Path, title_prefix: str = "", style: str = "github", 
                    use_fileio: bool = False, output_file: Optional[Path] = None,
                    append_id: Optional[str] = None, erase: bool = False,
                    debug: bool = False, fix_format: bool = False) -> List[str]:
    """Process all markdown files in a directory."""
    LOGGER.info(f"Processing all markdown files in {markdown_dir}")
    
    # Find all markdown files
    markdown_files = list(markdown_dir.glob("*.md"))
    if not markdown_files:
        LOGGER.error(f"No markdown files found in {markdown_dir}")
        return []
    
    LOGGER.info(f"Found {len(markdown_files)} markdown files to process")
    
    # Process each file
    results = []
    for markdown_path in sorted(markdown_files):
        try:
            url = process_markdown_file(
                markdown_path, title_prefix, style, use_fileio, 
                output_file, append_id, erase, debug, fix_format
            )
            if url:
                results.append(url)
        except Exception as e:
            LOGGER.error(f"Failed to process {markdown_path}: {e}")
    
    return results


def main():
    args = cli()
    setup_logging(args.log_level, args.log_file)
    
    # Verify installation if requested
    if args.verify_npm:
        if not verify_installation():
            LOGGER.error("Installation verification failed. Please install Node.js, npm, and md2gslides.")
            LOGGER.info("To install md2gslides: npm install -g md2gslides")
            sys.exit(1)
    
    # Validate the path
    markdown_path = Path(args.markdown)
    if not markdown_path.exists():
        LOGGER.error(f"{markdown_path} not found")
        
        # Check if there's a file with slides_ prefix
        parent_dir = markdown_path.parent
        basename = markdown_path.stem
        
        # Try with slides_ prefix
        alt_path = parent_dir / f"slides_{basename}.md"
        if alt_path.exists():
            LOGGER.info(f"Found alternative path: {alt_path}")
            markdown_path = alt_path
        else:
            # Look for any markdown file with similar name
            potential_files = list(parent_dir.glob(f"*{basename}*.md"))
            if potential_files:
                LOGGER.info(f"Found potential alternatives: {[p.name for p in potential_files]}")
                markdown_path = potential_files[0]
                LOGGER.info(f"Using {markdown_path}")
            else:
                LOGGER.error("No alternative markdown files found")
                sys.exit(1)
    
    # Determine output file
    output_file = Path(args.output_file) if args.output_file else None
    
    # If output file is specified, clear it
    if output_file:
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Presentations generated from {markdown_path}\n")
        except Exception as e:
            LOGGER.error(f"Error creating output file {output_file}: {e}")
            output_file = None
    
    # Process files
    try:
        if markdown_path.is_dir():
            results = process_directory(
                markdown_path, args.title_prefix, args.style, args.use_fileio, 
                output_file, args.append, args.erase, args.debug, args.fix_format
            )
            if results:
                LOGGER.info(f"Created {len(results)} presentations")
                if output_file:
                    LOGGER.info(f"Presentation URLs saved to {output_file}")
            else:
                LOGGER.warning("No presentations were created")
                sys.exit(1)
        else:
            url = process_markdown_file(
                markdown_path, args.title_prefix, args.style, args.use_fileio, 
                output_file, args.append, args.erase, args.debug, args.fix_format
            )
            if not url:
                LOGGER.error("Failed to create presentation")
                sys.exit(1)
    except Exception as e:
        LOGGER.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()