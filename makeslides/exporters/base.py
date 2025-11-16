#!/usr/bin/env python3
"""
Base class for presentation exporters.

All exporters should inherit from BaseExporter and implement the export() method.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base class for presentation exporters."""

    def __init__(self, slides_data: List[Dict[str, Any]], output_path: Optional[Path] = None):
        """
        Initialize the exporter.

        Args:
            slides_data: List of slide dictionaries (from JSON)
            output_path: Path for the output file
        """
        self.slides_data = slides_data
        self.output_path = output_path
        self.metadata = self._extract_metadata()

    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract presentation metadata from slides."""
        if not self.slides_data:
            return {}

        first_slide = self.slides_data[0]

        return {
            'title': first_slide.get('title', 'Untitled Presentation'),
            'subtitle': first_slide.get('content', ''),
            'author': '',
            'date': '',
            'total_slides': len(self.slides_data)
        }

    @abstractmethod
    def export(self) -> Path:
        """
        Export the presentation to the target format.

        Returns:
            Path to the generated file

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement export()")

    def validate_slides(self) -> bool:
        """
        Validate that slides data is properly formatted.

        Returns:
            True if valid, False otherwise
        """
        if not self.slides_data:
            logger.error("No slides data provided")
            return False

        if not isinstance(self.slides_data, list):
            logger.error("Slides data must be a list")
            return False

        for i, slide in enumerate(self.slides_data, 1):
            if not isinstance(slide, dict):
                logger.error(f"Slide {i} is not a dictionary")
                return False

            if 'title' not in slide:
                logger.warning(f"Slide {i} missing title field")

        return True

    def _sanitize_content(self, content: str) -> str:
        """
        Sanitize content for export.

        Args:
            content: Raw content string

        Returns:
            Sanitized content
        """
        if not content:
            return ""

        # Remove extra whitespace
        content = ' '.join(content.split())

        return content

    def _get_layout_type(self, slide: Dict[str, Any]) -> str:
        """
        Get the layout type for a slide.

        Args:
            slide: Slide dictionary

        Returns:
            Layout type string
        """
        layout = slide.get('layout', 'TITLE_AND_BODY')

        # Normalize layout names
        layout_map = {
            'TITLE': 'title',
            'TITLE_SLIDE': 'title',
            'title': 'title',
            'SECTION_HEADER': 'section',
            'section': 'section',
            'TITLE_AND_BODY': 'content',
            'content': 'content',
            'TITLE_AND_TWO_COLUMNS': 'two_columns',
            'TWO_COLUMNS': 'two_columns',
            'columns': 'two_columns',
            'two-column': 'two_columns',
            'QUOTE': 'quote',
            'quote': 'quote',
            'MAIN_POINT': 'main_point',
            'main_point': 'main_point',
            'BIG_NUMBER': 'big_number',
            'big_number': 'big_number',
            'CAPTION': 'caption',
            'caption': 'caption',
            'BLANK': 'blank',
            'blank': 'blank'
        }

        return layout_map.get(layout, 'content')

    def _format_bullet_points(self, content: str) -> List[str]:
        """
        Extract bullet points from content.

        Args:
            content: Content string with bullet points

        Returns:
            List of bullet point strings
        """
        if not content:
            return []

        lines = content.split('\n')
        bullets = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Remove bullet markers
            if line.startswith('* ') or line.startswith('- '):
                line = line[2:]
            elif line.startswith('• '):
                line = line[2:]

            bullets.append(line.strip())

        return bullets

    def __str__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(slides={len(self.slides_data)})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"{self.__class__.__name__}(slides={len(self.slides_data)}, output={self.output_path})"
