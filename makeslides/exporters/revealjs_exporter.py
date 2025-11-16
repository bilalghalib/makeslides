#!/usr/bin/env python3
"""
reveal.js exporter - creates beautiful HTML presentations.

reveal.js is a modern, feature-rich HTML presentation framework.
Output is a self-contained HTML file (or directory with assets).
"""
import logging
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

from .base import BaseExporter

logger = logging.getLogger(__name__)


class RevealJSExporter(BaseExporter):
    """Export presentations to reveal.js HTML format."""

    # reveal.js CDN version
    REVEALJS_VERSION = "4.6.0"

    # reveal.js themes
    THEMES = {
        'black': 'black',
        'white': 'white',
        'league': 'league',
        'beige': 'beige',
        'sky': 'sky',
        'night': 'night',
        'serif': 'serif',
        'simple': 'simple',
        'solarized': 'solarized',
        'moon': 'moon'
    }

    def __init__(self, slides_data: List[Dict[str, Any]], output_path: Optional[Path] = None,
                 theme: str = "black", embed_images: bool = True):
        """
        Initialize reveal.js exporter.

        Args:
            slides_data: List of slide dictionaries
            output_path: Path for output HTML file
            theme: reveal.js theme name
            embed_images: If True, embed images as base64 (for offline use)
        """
        super().__init__(slides_data, output_path)
        self.theme = theme if theme in self.THEMES else 'black'
        self.embed_images = embed_images

    def export(self) -> Path:
        """
        Export presentation to reveal.js HTML file.

        Returns:
            Path to the generated HTML file
        """
        if not self.validate_slides():
            raise ValueError("Invalid slides data")

        logger.info(f"Exporting {len(self.slides_data)} slides to reveal.js...")

        # Generate HTML
        html = self._generate_html()

        # Determine output path
        if not self.output_path:
            title_slug = self.metadata['title'].lower().replace(' ', '_')
            self.output_path = Path(f"{title_slug}_revealjs.html")

        # Write HTML file
        self.output_path.write_text(html, encoding='utf-8')
        logger.info(f"✅ reveal.js presentation saved to: {self.output_path}")
        logger.info(f"   Open in browser to view: file://{self.output_path.absolute()}")

        return self.output_path

    def _generate_html(self) -> str:
        """Generate complete HTML document."""
        slides_html = self._generate_slides_html()

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.metadata['title']}</title>

    <!-- reveal.js CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/dist/reset.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/dist/theme/{self.theme}.css">

    <!-- Syntax highlighting -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/plugin/highlight/monokai.css">

    <style>
        /* Custom styles */
        .reveal h1 {{ text-transform: none; }}
        .reveal h2 {{ text-transform: none; }}
        .reveal h3 {{ text-transform: none; }}

        .reveal .slides section.title-slide {{
            text-align: center;
        }}

        .reveal .slides section.section-header {{
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}

        .reveal .slides section.section-header h2 {{
            color: white;
            font-size: 3em;
            font-weight: bold;
        }}

        .reveal .slides section.two-column {{
            display: flex;
        }}

        .reveal .slides section.two-column .column {{
            flex: 1;
            padding: 0 1em;
        }}

        .reveal .slides section.quote {{
            text-align: center;
        }}

        .reveal .slides section.quote blockquote {{
            font-size: 1.5em;
            font-style: italic;
            border-left: 5px solid #667eea;
            padding-left: 20px;
        }}

        .reveal .slides section.main-point {{
            text-align: center;
        }}

        .reveal .slides section.main-point h2 {{
            font-size: 4em;
            font-weight: bold;
            color: #667eea;
        }}

        .reveal .slides section.big-number {{
            text-align: center;
        }}

        .reveal .slides section.big-number .number {{
            font-size: 6em;
            font-weight: bold;
            color: #ff6b6b;
        }}

        .reveal .slides section.big-number .description {{
            font-size: 1.5em;
            margin-top: 0.5em;
        }}

        .reveal img {{
            max-width: 100%;
            max-height: 500px;
        }}

        .reveal .speaker-notes {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
{slides_html}
        </div>
    </div>

    <!-- reveal.js scripts -->
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/dist/reveal.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/plugin/notes/notes.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/plugin/markdown/markdown.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/plugin/highlight/highlight.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@{self.REVEALJS_VERSION}/plugin/zoom/zoom.js"></script>

    <script>
        // Initialize reveal.js
        Reveal.initialize({{
            hash: true,
            transition: 'slide',
            transitionSpeed: 'default',
            backgroundTransition: 'fade',
            slideNumber: true,
            controls: true,
            progress: true,
            center: true,
            touch: true,
            overview: true,
            help: true,

            // Plugins
            plugins: [ RevealMarkdown, RevealHighlight, RevealNotes, RevealZoom ]
        }});
    </script>
</body>
</html>'''

        return html

    def _generate_slides_html(self) -> str:
        """Generate HTML for all slides."""
        slides = []

        for slide_data in self.slides_data:
            slide_html = self._generate_slide_html(slide_data)
            slides.append(slide_html)

        return '\n'.join(slides)

    def _generate_slide_html(self, slide_data: Dict[str, Any]) -> str:
        """Generate HTML for a single slide."""
        layout_type = self._get_layout_type(slide_data)

        # Map layout types to generation methods
        layout_methods = {
            'title': self._generate_title_slide,
            'section': self._generate_section_slide,
            'content': self._generate_content_slide,
            'two_columns': self._generate_two_column_slide,
            'quote': self._generate_quote_slide,
            'main_point': self._generate_main_point_slide,
            'big_number': self._generate_big_number_slide,
            'caption': self._generate_caption_slide,
            'blank': self._generate_blank_slide
        }

        method = layout_methods.get(layout_type, self._generate_content_slide)
        return method(slide_data)

    def _generate_title_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate title slide HTML."""
        title = slide_data.get('title', '')
        content = slide_data.get('content', '')
        notes = self._generate_notes(slide_data)

        return f'''
            <section class="title-slide">
                <h1>{self._escape_html(title)}</h1>
                <p>{self._escape_html(content)}</p>
                {notes}
            </section>'''

    def _generate_section_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate section header slide HTML."""
        title = slide_data.get('title', '')
        notes = self._generate_notes(slide_data)

        return f'''
            <section class="section-header">
                <h2>{self._escape_html(title)}</h2>
                {notes}
            </section>'''

    def _generate_content_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate content slide with bullet points."""
        title = slide_data.get('title', '')
        content = slide_data.get('content', '')
        notes = self._generate_notes(slide_data)

        # Format bullet points
        bullets = self._format_bullet_points(content)
        bullets_html = '<ul>\n'
        for bullet in bullets:
            bullets_html += f'    <li>{self._escape_html(bullet)}</li>\n'
        bullets_html += '</ul>'

        # Add image if present
        image_html = self._generate_image_html(slide_data)

        return f'''
            <section>
                <h2>{self._escape_html(title)}</h2>
                {bullets_html}
                {image_html}
                {notes}
            </section>'''

    def _generate_two_column_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate two-column layout slide."""
        title = slide_data.get('title', '')
        content = slide_data.get('content', '')
        notes = self._generate_notes(slide_data)

        # Split content
        if '|' in content:
            left_content, right_content = content.split('|', 1)
        else:
            bullets = self._format_bullet_points(content)
            mid = len(bullets) // 2
            left_content = '\n'.join(bullets[:mid])
            right_content = '\n'.join(bullets[mid:])

        # Format as bullet lists
        left_bullets = self._format_bullet_points(left_content)
        right_bullets = self._format_bullet_points(right_content)

        left_html = '<ul>\n' + ''.join(f'    <li>{self._escape_html(b)}</li>\n' for b in left_bullets) + '</ul>'

        # Check for image in right column
        image_url = slide_data.get('image_url')
        if image_url and not 'diagram' in image_url.lower():
            right_html = self._generate_image_html(slide_data)
        else:
            right_html = '<ul>\n' + ''.join(f'    <li>{self._escape_html(b)}</li>\n' for b in right_bullets) + '</ul>'

        return f'''
            <section class="two-column">
                <h2 style="width: 100%">{self._escape_html(title)}</h2>
                <div class="column">
                    {left_html}
                </div>
                <div class="column">
                    {right_html}
                </div>
                {notes}
            </section>'''

    def _generate_quote_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate quote slide."""
        title = slide_data.get('title', '')
        content = slide_data.get('content', '')
        notes = self._generate_notes(slide_data)

        return f'''
            <section class="quote">
                <blockquote>
                    "{self._escape_html(content)}"
                </blockquote>
                <p><em>— {self._escape_html(title)}</em></p>
                {notes}
            </section>'''

    def _generate_main_point_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate main point slide."""
        title = slide_data.get('title', '')
        content = slide_data.get('content', '')
        notes = self._generate_notes(slide_data)

        content_html = f'<p>{self._escape_html(content)}</p>' if content else ''

        return f'''
            <section class="main-point">
                <h2>{self._escape_html(title)}</h2>
                {content_html}
                {notes}
            </section>'''

    def _generate_big_number_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate big number slide."""
        title = slide_data.get('title', '')
        content = slide_data.get('content', '')
        notes = self._generate_notes(slide_data)

        return f'''
            <section class="big-number">
                <div class="number">{self._escape_html(title)}</div>
                <div class="description">{self._escape_html(content)}</div>
                {notes}
            </section>'''

    def _generate_caption_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate image with caption slide."""
        title = slide_data.get('title', '')
        notes = self._generate_notes(slide_data)
        image_html = self._generate_image_html(slide_data)

        return f'''
            <section>
                {image_html}
                <p><em>{self._escape_html(title)}</em></p>
                {notes}
            </section>'''

    def _generate_blank_slide(self, slide_data: Dict[str, Any]) -> str:
        """Generate blank slide with background image."""
        notes = self._generate_notes(slide_data)
        image_url = slide_data.get('image_url', '')

        if image_url:
            # Use as background
            bg_image = self._process_image_url(image_url)
            return f'''
            <section data-background-image="{bg_image}" data-background-size="cover">
                {notes}
            </section>'''
        else:
            return f'<section>{notes}</section>'

    def _generate_image_html(self, slide_data: Dict[str, Any]) -> str:
        """Generate HTML for an image."""
        image_url = slide_data.get('image_url')

        if not image_url:
            return ''

        processed_url = self._process_image_url(image_url)
        alt_text = slide_data.get('title', 'Image')

        return f'<img src="{processed_url}" alt="{self._escape_html(alt_text)}">'

    def _process_image_url(self, image_url: str) -> str:
        """
        Process image URL - embed as base64 if configured, otherwise return URL.
        """
        if not self.embed_images:
            return image_url

        # Only embed for HTTP URLs (local files are already accessible)
        if not image_url.startswith('http'):
            return image_url

        try:
            logger.info(f"Embedding image: {image_url}")
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Detect content type
            content_type = response.headers.get('content-type', 'image/png')

            # Encode to base64
            b64_data = base64.b64encode(response.content).decode('utf-8')

            return f"data:{content_type};base64,{b64_data}"

        except Exception as e:
            logger.warning(f"Failed to embed image {image_url}: {e}")
            return image_url

    def _generate_notes(self, slide_data: Dict[str, Any]) -> str:
        """Generate speaker notes HTML."""
        notes = slide_data.get('facilitator_notes', '')

        if not notes:
            return ''

        return f'''
                <aside class="notes">
                    {self._escape_html(notes)}
                </aside>'''

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ''

        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))


def export_to_revealjs(slides_data: List[Dict[str, Any]], output_path: Optional[Path] = None,
                       theme: str = "black", embed_images: bool = True) -> Path:
    """
    Convenience function to export slides to reveal.js.

    Args:
        slides_data: List of slide dictionaries
        output_path: Output file path
        theme: reveal.js theme name
        embed_images: Whether to embed images as base64

    Returns:
        Path to generated HTML file
    """
    exporter = RevealJSExporter(slides_data, output_path, theme, embed_images)
    return exporter.export()
