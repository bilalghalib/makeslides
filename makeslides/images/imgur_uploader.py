#!/usr/bin/env python3
"""
Imgur API image uploader - replaces temporary litterbox hosting.

Free tier allows unlimited anonymous uploads with permanent hosting.
Images uploaded anonymously can be deleted within the first 24 hours.
"""
import os
import sys
import time
import logging
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Imgur API configuration
IMGUR_API_URL = "https://api.imgur.com/3/upload"
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID", "546c25a59c58ad7")  # Public anonymous client ID

class ImgurUploader:
    """Upload images to Imgur for permanent hosting."""

    def __init__(self, client_id: Optional[str] = None):
        """
        Initialize Imgur uploader.

        Args:
            client_id: Imgur API client ID. If not provided, uses anonymous uploads.
        """
        self.client_id = client_id or IMGUR_CLIENT_ID
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Client-ID {self.client_id}"
        })

    def upload_image(self, image_path: str, title: Optional[str] = None,
                    description: Optional[str] = None, max_retries: int = 3) -> Optional[str]:
        """
        Upload an image to Imgur.

        Args:
            image_path: Path to the image file
            title: Optional title for the image
            description: Optional description
            max_retries: Number of retry attempts

        Returns:
            Direct URL to the uploaded image, or None on failure
        """
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None

        # Validate file size (Imgur has a 10MB limit for anonymous uploads)
        file_size = os.path.getsize(image_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            logger.error(f"Image too large: {file_size / 1024 / 1024:.2f}MB (max 10MB)")
            return None

        logger.info(f"Uploading {image_path} to Imgur...")

        for attempt in range(max_retries):
            try:
                # Read image and encode to base64
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                # Prepare payload
                payload = {
                    'image': image_data,
                    'type': 'base64'
                }

                if title:
                    payload['title'] = title
                if description:
                    payload['description'] = description

                # Upload to Imgur
                response = self.session.post(IMGUR_API_URL, data=payload)

                if response.status_code == 200:
                    data = response.json()

                    if data.get('success'):
                        # Get the direct link to the image
                        image_url = data['data']['link']
                        delete_hash = data['data'].get('deletehash')

                        logger.info(f"✅ Successfully uploaded to Imgur: {image_url}")
                        if delete_hash:
                            logger.info(f"   Delete hash (save this to delete within 24h): {delete_hash}")

                        return image_url
                    else:
                        logger.error(f"Upload failed: {data.get('data', {}).get('error', 'Unknown error')}")

                elif response.status_code == 429:
                    # Rate limit hit
                    logger.warning(f"Rate limit hit, waiting before retry...")
                    time.sleep(2 ** attempt)

                else:
                    logger.error(f"Upload failed with status {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Upload attempt {attempt + 1}/{max_retries} failed: {e}")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

            except Exception as e:
                logger.error(f"Unexpected error during upload: {e}")
                return None

        logger.error(f"Failed to upload image after {max_retries} attempts")
        return None

    def upload_directory(self, directory: str, pattern: str = "*.png") -> Dict[str, str]:
        """
        Upload all images in a directory matching a pattern.

        Args:
            directory: Directory containing images
            pattern: Glob pattern for files to upload (e.g., "*.png", "*.jpg")

        Returns:
            Dictionary mapping local paths to Imgur URLs
        """
        dir_path = Path(directory)

        if not dir_path.exists() or not dir_path.is_dir():
            logger.error(f"Directory not found: {directory}")
            return {}

        image_files = list(dir_path.glob(pattern))

        if not image_files:
            logger.warning(f"No images found matching {pattern} in {directory}")
            return {}

        logger.info(f"Found {len(image_files)} images to upload")

        url_mapping = {}

        for i, image_path in enumerate(image_files, 1):
            logger.info(f"Uploading {i}/{len(image_files)}: {image_path.name}")

            # Create title from filename
            title = image_path.stem.replace('_', ' ').title()

            url = self.upload_image(str(image_path), title=title)

            if url:
                url_mapping[str(image_path)] = url
                # Small delay to avoid rate limiting
                if i < len(image_files):
                    time.sleep(0.5)
            else:
                logger.warning(f"Failed to upload {image_path.name}")

        logger.info(f"Successfully uploaded {len(url_mapping)}/{len(image_files)} images")

        return url_mapping

    @staticmethod
    def is_imgur_url(url: str) -> bool:
        """Check if a URL is an Imgur URL."""
        parsed = urlparse(url)
        return 'imgur.com' in parsed.netloc.lower()


def upload_image(image_path: str, client_id: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to upload a single image.

    Args:
        image_path: Path to the image file
        client_id: Optional Imgur client ID

    Returns:
        Direct URL to the uploaded image, or None on failure
    """
    uploader = ImgurUploader(client_id=client_id)
    return uploader.upload_image(image_path)


def main():
    """CLI for testing Imgur uploads."""
    import argparse

    parser = argparse.ArgumentParser(description="Upload images to Imgur")
    parser.add_argument("image", help="Path to image file or directory")
    parser.add_argument("--directory", action="store_true", help="Upload all images in directory")
    parser.add_argument("--pattern", default="*.png", help="File pattern for directory mode")
    parser.add_argument("--client-id", help="Imgur API client ID (optional)")
    parser.add_argument("--title", help="Image title")
    parser.add_argument("--description", help="Image description")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    uploader = ImgurUploader(client_id=args.client_id)

    if args.directory:
        # Upload directory
        urls = uploader.upload_directory(args.image, pattern=args.pattern)

        print(f"\n{'='*60}")
        print(f"Uploaded {len(urls)} images:")
        print(f"{'='*60}")

        for local_path, url in urls.items():
            print(f"{Path(local_path).name}: {url}")

    else:
        # Upload single file
        url = uploader.upload_image(args.image, title=args.title, description=args.description)

        if url:
            print(f"\n{'='*60}")
            print(f"Image uploaded successfully!")
            print(f"{'='*60}")
            print(f"URL: {url}")
        else:
            print("Upload failed!")
            sys.exit(1)


if __name__ == "__main__":
    main()
