#!/usr/bin/env python3
"""
Asset Manager for MakeSlides

This script provides centralized management for all assets (images, diagrams)
used in the slide creation process. It maintains a cache of assets to avoid
redundant downloads and generation.
"""
from __future__ import annotations
import argparse, json, logging, os, sys, shutil, hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
import time

LOGGER = logging.getLogger("asset_manager")

# Default paths
DEFAULT_CACHE_DIR = Path.home() / ".makeslides" / "assets"
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "asset_cache.json"

def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Manage assets for MakeSlides")
    
    # Command subparsers
    subparsers = p.add_subparsers(dest="command", help="Command to execute")
    
    # Get image command
    get_img = subparsers.add_parser("get-image", help="Get or cache an image")
    get_img.add_argument("url", help="URL of the image to get")
    get_img.add_argument("--category", help="Category for the image (e.g., 'solar', 'training')")
    get_img.add_argument("--local-path", help="Optional local path to store/copy the image")
    
    # Get diagram command
    get_diag = subparsers.add_parser("get-diagram", help="Get or cache a diagram")
    get_diag.add_argument("content", help="Mermaid content of the diagram")
    get_diag.add_argument("--type", default="flowchart", help="Type of diagram")
    get_diag.add_argument("--local-path", help="Optional local path to store the diagram")
    
    # List assets command
    list_cmd = subparsers.add_parser("list", help="List all cached assets")
    list_cmd.add_argument("--category", help="Filter by category")
    list_cmd.add_argument("--type", help="Filter by asset type (image/diagram)")
    
    # Clean cache command
    clean_cmd = subparsers.add_parser("clean", help="Clean the asset cache")
    clean_cmd.add_argument("--remove-unused", action="store_true", help="Remove unused assets")
    clean_cmd.add_argument("--days", type=int, default=30, help="Remove assets older than X days")
    
    # Update JSON command
    update_cmd = subparsers.add_parser("update-json", help="Update JSON files with asset paths")
    update_cmd.add_argument("json_file", help="JSON file to update")
    update_cmd.add_argument("--output", help="Output file (default: overwrite input)")
    
    # Common arguments
    p.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="Cache directory")
    p.add_argument("--cache-file", default=DEFAULT_CACHE_FILE, help="Cache file")
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    return p.parse_args()

def setup_logging(level: str):
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

class AssetManager:
    """Manages assets (images, diagrams) for slide creation."""
    
    def __init__(self, cache_dir: Path, cache_file: Path):
        """Initialize the asset manager.
        
        Args:
            cache_dir: Directory to store cached assets
            cache_file: File to store cache metadata
        """
        self.cache_dir = cache_dir
        self.images_dir = cache_dir / "images"
        self.diagrams_dir = cache_dir / "diagrams"
        self.cache_file = cache_file
        
        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        self.diagrams_dir.mkdir(exist_ok=True)
        
        # Load cache
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load the asset cache from disk."""
        if not self.cache_file.exists():
            LOGGER.info(f"Cache file not found at {self.cache_file}. Creating new cache.")
            return {
                "images": {},
                "diagrams": {},
                "last_updated": time.time()
            }
        
        try:
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
            LOGGER.debug(f"Loaded cache with {len(cache.get('images', {}))} images and {len(cache.get('diagrams', {}))} diagrams")
            return cache
        except Exception as e:
            LOGGER.warning(f"Error loading cache: {e}. Creating new cache.")
            return {
                "images": {},
                "diagrams": {},
                "last_updated": time.time()
            }
    
    def _save_cache(self):
        """Save the asset cache to disk."""
        self.cache["last_updated"] = time.time()
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
            LOGGER.debug(f"Saved cache to {self.cache_file}")
        except Exception as e:
            LOGGER.error(f"Error saving cache: {e}")
    
    def get_image(self, url: str, category: Optional[str] = None, local_path: Optional[Path] = None) -> Path:
        """Get or cache an image.
        
        Args:
            url: URL of the image
            category: Category for the image (e.g., 'solar', 'training')
            local_path: Optional local path to store/copy the image
            
        Returns:
            Path to the cached image
        """
        # Generate a hash for the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
        
        # Check if image is already in cache
        if url in self.cache["images"]:
            cached_path = Path(self.cache["images"][url]["path"])
            if cached_path.exists():
                LOGGER.info(f"Using cached image for {url}")
                
                # If local_path is provided, copy the image
                if local_path:
                    local_path = Path(local_path)
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(cached_path, local_path)
                    LOGGER.debug(f"Copied cached image to {local_path}")
                    return local_path
                
                return cached_path
        
        # Image not in cache or file missing, download it
        LOGGER.info(f"Downloading image from {url}")
        
        try:
            # Determine file extension from URL
            ext = Path(url).suffix
            if not ext:
                ext = ".jpg"  # Default to jpg if no extension
            
            # Create filename and path
            filename = f"img_{url_hash}{ext}"
            img_path = self.images_dir / filename
            
            # Download the image
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            
            with open(img_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Update cache
            self.cache["images"][url] = {
                "path": str(img_path),
                "category": category,
                "hash": url_hash,
                "timestamp": time.time()
            }
            self._save_cache()
            
            # If local_path is provided, copy the image
            if local_path:
                local_path = Path(local_path)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(img_path, local_path)
                LOGGER.debug(f"Copied downloaded image to {local_path}")
                return local_path
            
            return img_path
            
        except Exception as e:
            LOGGER.error(f"Error downloading image from {url}: {e}")
            raise
    
    def get_diagram(self, content: str, diagram_type: str = "flowchart", local_path: Optional[Path] = None) -> Optional[Path]:
        """Get or cache a diagram.
        
        Args:
            content: Mermaid content of the diagram
            diagram_type: Type of diagram (e.g., 'flowchart', 'mindmap')
            local_path: Optional local path to store the diagram
            
        Returns:
            Path to the cached diagram or None if not found
        """
        # Generate a hash for the content
        content_hash = hashlib.md5(content.encode()).hexdigest()[:10]
        
        # Check if diagram is already in cache
        if content_hash in self.cache["diagrams"]:
            cached_info = self.cache["diagrams"][content_hash]
            cached_path = Path(cached_info["path"])
            
            if cached_path.exists():
                LOGGER.info(f"Using cached diagram for hash {content_hash}")
                
                # If local_path is provided, copy the diagram
                if local_path:
                    local_path = Path(local_path)
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(cached_path, local_path)
                    
                    # Also copy SVG if it exists
                    svg_path = cached_path.with_suffix(".svg")
                    if svg_path.exists():
                        local_svg_path = local_path.with_suffix(".svg")
                        shutil.copy2(svg_path, local_svg_path)
                        LOGGER.debug(f"Copied cached SVG to {local_svg_path}")
                    
                    LOGGER.debug(f"Copied cached diagram to {local_path}")
                    return local_path
                
                return cached_path
        
        # If we're just checking and not generating, return None
        if local_path is None:
            LOGGER.info(f"Diagram {content_hash} not found in cache")
            return None
        
        # If local_path is provided, assume it's a newly generated diagram we want to cache
        if local_path:
            local_path = Path(local_path)
            if local_path.exists():
                # Create cached copy
                cached_filename = f"diagram_{content_hash}{local_path.suffix}"
                cached_path = self.diagrams_dir / cached_filename
                
                # Copy to cache
                shutil.copy2(local_path, cached_path)
                LOGGER.info(f"Cached new diagram as {cached_path}")
                
                # Also copy SVG if it exists
                local_svg_path = local_path.with_suffix(".svg")
                if local_svg_path.exists():
                    cached_svg_path = cached_path.with_suffix(".svg")
                    shutil.copy2(local_svg_path, cached_svg_path)
                    LOGGER.debug(f"Cached SVG as {cached_svg_path}")
                
                # Update cache
                self.cache["diagrams"][content_hash] = {
                    "path": str(cached_path),
                    "type": diagram_type,
                    "hash": content_hash,
                    "timestamp": time.time()
                }
                self._save_cache()
                
                return local_path
        
        LOGGER.error(f"No local path provided for diagram {content_hash}")
        return None
    
    def list_assets(self, category: Optional[str] = None, asset_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """List all cached assets, optionally filtered by category or type.
        
        Args:
            category: Filter by category
            asset_type: Filter by asset type (image/diagram)
            
        Returns:
            Dictionary with lists of assets
        """
        result = {"images": [], "diagrams": []}
        
        # Filter images
        if asset_type is None or asset_type == "image":
            for url, info in self.cache["images"].items():
                if category is None or info.get("category") == category:
                    asset_path = Path(info["path"])
                    if asset_path.exists():
                        result["images"].append({
                            "url": url,
                            "path": info["path"],
                            "category": info.get("category"),
                            "timestamp": info.get("timestamp", 0)
                        })
        
        # Filter diagrams
        if asset_type is None or asset_type == "diagram":
            for content_hash, info in self.cache["diagrams"].items():
                asset_path = Path(info["path"])
                if asset_path.exists():
                    result["diagrams"].append({
                        "hash": content_hash,
                        "path": info["path"],
                        "type": info.get("type"),
                        "timestamp": info.get("timestamp", 0)
                    })
        
        return result
    
    def clean_cache(self, remove_unused: bool = False, days: int = 30) -> Tuple[int, int]:
        """Clean the asset cache.
        
        Args:
            remove_unused: Whether to remove unused assets
            days: Remove assets older than X days
            
        Returns:
            Tuple of (images_removed, diagrams_removed)
        """
        now = time.time()
        threshold = now - (days * 86400)  # Convert days to seconds
        
        images_removed = 0
        diagrams_removed = 0
        
        # Clean images
        images_to_remove = []
        for url, info in self.cache["images"].items():
            if remove_unused or info.get("timestamp", 0) < threshold:
                try:
                    path = Path(info["path"])
                    if path.exists():
                        path.unlink()
                        images_removed += 1
                    images_to_remove.append(url)
                except Exception as e:
                    LOGGER.warning(f"Error removing image {url}: {e}")
        
        # Remove from cache
        for url in images_to_remove:
            del self.cache["images"][url]
        
        # Clean diagrams
        diagrams_to_remove = []
        for content_hash, info in self.cache["diagrams"].items():
            if remove_unused or info.get("timestamp", 0) < threshold:
                try:
                    path = Path(info["path"])
                    if path.exists():
                        path.unlink()
                        # Also remove SVG if it exists
                        svg_path = path.with_suffix(".svg")
                        if svg_path.exists():
                            svg_path.unlink()
                        diagrams_removed += 1
                    diagrams_to_remove.append(content_hash)
                except Exception as e:
                    LOGGER.warning(f"Error removing diagram {content_hash}: {e}")
        
        # Remove from cache
        for content_hash in diagrams_to_remove:
            del self.cache["diagrams"][content_hash]
        
        # Save cache
        self._save_cache()
        
        return images_removed, diagrams_removed
    
    def update_json(self, json_path: Path, output_path: Optional[Path] = None) -> int:
        """Update a slides JSON file with cached asset paths.
        
        Args:
            json_path: Path to the JSON file
            output_path: Optional output path (default: overwrite input)
            
        Returns:
            Number of assets updated
        """
        try:
            with open(json_path, 'r') as f:
                slides_data = json.load(f)
        except Exception as e:
            LOGGER.error(f"Error loading JSON from {json_path}: {e}")
            return 0
        
        # Check if it's an object with a slides array
        if isinstance(slides_data, dict) and "slides" in slides_data:
            slides = slides_data["slides"]
        elif isinstance(slides_data, list):
            slides = slides_data
        else:
            LOGGER.error(f"Unexpected JSON structure in {json_path}")
            return 0
        
        assets_updated = 0
        
        # Update each slide
        for slide in slides:
            # Update image URLs
            image_url = slide.get("image_url")
            if image_url and image_url.startswith("http"):
                try:
                    # Check if the image is in the cache
                    if image_url in self.cache["images"]:
                        cached_path = Path(self.cache["images"][image_url]["path"])
                        if cached_path.exists():
                            # Use relative path from JSON file to cached image
                            try:
                                json_dir = json_path.parent
                                rel_path = cached_path.relative_to(json_dir)
                                slide["image_url"] = str(rel_path)
                                assets_updated += 1
                                LOGGER.debug(f"Updated image URL to {rel_path}")
                            except ValueError:
                                # If the cached path is not relative to the JSON file,
                                # download and cache it in the same directory
                                new_path = json_dir / "images" / cached_path.name
                                new_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(cached_path, new_path)
                                rel_path = new_path.relative_to(json_dir)
                                slide["image_url"] = str(rel_path)
                                assets_updated += 1
                                LOGGER.debug(f"Copied image to {rel_path}")
                    else:
                        # Download and cache the image
                        img_dir = json_path.parent / "images"
                        img_dir.mkdir(parents=True, exist_ok=True)
                        img_file = img_dir / f"img_{hashlib.md5(image_url.encode()).hexdigest()[:10]}.jpg"
                        cached_path = self.get_image(image_url, local_path=img_file)
                        rel_path = cached_path.relative_to(json_path.parent)
                        slide["image_url"] = str(rel_path)
                        assets_updated += 1
                        LOGGER.debug(f"Downloaded and cached image to {rel_path}")
                except Exception as e:
                    LOGGER.warning(f"Error updating image URL {image_url}: {e}")
            
            # Cache diagram content
            diagram_content = slide.get("diagram_content")
            diagram_type = slide.get("diagram_type")
            
            if diagram_content and diagram_type:
                content_hash = hashlib.md5(diagram_content.encode()).hexdigest()[:10]
                if content_hash in self.cache["diagrams"]:
                    # Diagram already in cache, nothing to do
                    pass
                else:
                    # Check if diagram files exist
                    json_dir = json_path.parent
                    img_url = slide.get("image_url")
                    
                    if img_url and not img_url.startswith("http"):
                        img_path = json_dir / img_url
                        if img_path.exists():
                            # Cache the existing diagram
                            self.get_diagram(diagram_content, diagram_type, local_path=img_path)
                            assets_updated += 1
                            LOGGER.debug(f"Cached existing diagram from {img_path}")
        
        # Save the updated JSON
        if output_path:
            out_path = Path(output_path)
        else:
            out_path = json_path
        
        try:
            if isinstance(slides_data, dict) and "slides" in slides_data:
                slides_data["slides"] = slides
                with open(out_path, 'w') as f:
                    json.dump(slides_data, f, indent=2)
            else:
                with open(out_path, 'w') as f:
                    json.dump(slides, f, indent=2)
            
            LOGGER.info(f"Updated {assets_updated} assets in {out_path}")
        except Exception as e:
            LOGGER.error(f"Error saving updated JSON: {e}")
        
        return assets_updated

def main():
    args = cli()
    setup_logging(args.log_level)
    
    # Create asset manager
    cache_dir = Path(args.cache_dir)
    cache_file = Path(args.cache_file)
    manager = AssetManager(cache_dir, cache_file)
    
    # Execute command
    if args.command == "get-image":
        local_path = Path(args.local_path) if args.local_path else None
        path = manager.get_image(args.url, args.category, local_path)
        print(f"Image cached at: {path}")
    
    elif args.command == "get-diagram":
        local_path = Path(args.local_path) if args.local_path else None
        path = manager.get_diagram(args.content, args.type, local_path)
        if path:
            print(f"Diagram cached at: {path}")
        else:
            print("Diagram not found in cache and no local path provided")
    
    elif args.command == "list":
        assets = manager.list_assets(args.category, args.type)
        print("\nImages:")
        for img in assets["images"]:
            print(f"  - {img['url']} -> {img['path']}")
        
        print("\nDiagrams:")
        for diag in assets["diagrams"]:
            print(f"  - {diag['hash']} ({diag['type']}) -> {diag['path']}")
    
    elif args.command == "clean":
        images, diagrams = manager.clean_cache(args.remove_unused, args.days)
        print(f"Removed {images} images and {diagrams} diagrams from cache")
    
    elif args.command == "update-json":
        json_path = Path(args.json_file)
        output_path = Path(args.output) if args.output else None
        assets_updated = manager.update_json(json_path, output_path)
        print(f"Updated {assets_updated} assets in {json_path}")
    
    else:
        print("No command specified. Use --help for usage information.")

if __name__ == "__main__":
    main()
