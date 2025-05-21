# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MakeSlides is a CLI tool for converting training facilitator guides into Google Slides presentations. The workflow involves:

1. Converting a facilitator guide document into a structured JSON file using Claude API
2. Using the JSON data to generate a Google Slides presentation with locally stored images and diagrams
3. Automatically uploading and embedding images for proper display in Google Slides

## Architecture

The codebase consists of these main components:

1. **Guide to JSON Processor (`guide/parser.py`)** - Converts facilitator guides to structured JSON:
   - Uses Claude API to analyze and structure guide content
   - Extracts slide content, titles, diagrams, and metadata
   - Normalizes output and validates JSON formatting
   - Applies layout mappings and defaults

2. **Diagram Generator (`diagrams/renderer.py`)** - Creates diagrams from Mermaid syntax:
   - Validates and repairs common Mermaid syntax issues
   - Generates PNG and SVG diagrams from Mermaid specifications
   - Uses Claude API to fix syntax errors and convert text to diagrams
   - Handles error cases with fallback diagrams

3. **Markdown Generator (`markdown/generator.py`)** - Converts JSON to markdown for slide creation:
   - Processes JSON slide data into markdown slides
   - Handles diagrams and images
   - Creates content formatted specifically for md2gslides

4. **Slides Generator (`slides/builder.py`)** - Creates Google Slides presentations:
   - Uses md2gslides npm package to create presentations
   - Validates markdown content
   - Handles image and diagram embedding
   - Provides detailed logging and error handling

5. **Asset Manager (`assets/asset_manager.py`)** - Manages image and diagram assets:
   - Caches diagrams to avoid regeneration
   - Provides consistent file naming
   - Handles storage and retrieval of assets

6. **Markdown Formatter (`markdown/formatter.py`)** - Enhances markdown for better slide formatting:
   - Improves bullet point and list formatting
   - Properly formats agenda and schedule slides
   - Enhances two-column layout rendering
   - Ensures proper spacing and indentation

7. **Image Processing Tools**:
   - **`scripts/upload_and_fix_images.py`** - Comprehensive image processing solution:
     - Finds images referenced in JSON and markdown
     - Uploads images to temporary hosting service
     - Updates markdown with remote image URLs
     - Generates Google Slides with properly displayed images
   - **`scripts/direct_image_fixer.py`** - Direct approach to image URL replacement
   - **`markdown/embed_images.py`** - Alternative solution that embeds SVG content directly

8. **Workflow Wrapper (`scripts/magicSlide.sh`)** - Combines all processing steps:
   - Manages the complete workflow from guide to presentation
   - Handles both single files and directories
   - Creates and verifies required directories
   - Coordinates all processing stages
   - Provides extensive command-line options for customization

## Commands

### Recommended Workflow (Automated)

The most efficient workflow uses the magicSlide.sh script with the new image processing tools:

1. **Complete workflow with automatic image processing**:
   ```bash
   ./magicSlide.sh guides/day2.md --stop-after=4
   python upload_and_fix_images.py slides_day2.md
   ```
   This processes the guide, creates markdown, uploads all images, and generates Google Slides with properly displayed images.

2. **Using the all-in-one slidify-wrap.py**:
   ```bash
   python slidify-wrap.py guides/day2.md
   ```
   This handles the entire process from guide to presentation with proper image handling.

### Step-by-Step Usage

If you need to run each step individually:

1. **Process a facilitator guide to JSON**:
   ```bash
   python guide_to_json.py guides/day2.md
   ```
   This creates `slides_day2.json` in the current directory.

2. **Generate diagrams from the JSON**:
   ```bash
   python diagrams_to_images.py slides_day2.json
   ```
   This renders diagrams and saves them to the `images/` directory.

3. **Convert JSON to markdown**:
   ```bash
   python json_to_markdown.py slides_day2.json
   ```
   This creates `slides_day2.md` for use with md2gslides.

4. **Format the markdown for better rendering**:
   ```bash
   python format-markdown.py slides_day2.md
   ```
   This improves formatting of bullet points, agendas, and column layouts.

5. **Process images for Google Slides compatibility**:
   ```bash
   python upload_and_fix_images.py slides_day2.md
   ```
   This finds, uploads, and updates image references in the markdown before creating the slides.

6. **Alternative image processing options**:
   - For direct image fixing:
     ```bash
     python direct_image_fixer.py slides_day2.md
     ```
   - For SVG embedding approach:
     ```bash
     python embed_images.py slides_day2.md
     ```
   - For manual image uploads:
     ```bash
     ./upload_temp_image.sh path/to/image.png [expiry_time]
     ```
     Where expiry_time can be 1h, 12h, 24h, or 72h (default: 24h).

7. **Manual Google Slides generation** (if not using automated tools):
   ```bash
   python build_with_md2gslides.py slides_day2.md --fix-format --use-fileio
   ```
   This creates a Google Slides presentation and returns the URL.

## Configuration Files

1. **config.yaml** - Contains the prompt template for Claude to process facilitator guides:
   - Controls the prompt for LLM processing
   - Defines layout mappings
   - Sets slide defaults

2. **mermaid-config.json** - Configuration for Mermaid diagram generation:
   - Defines styling for diagrams
   - Sets default theme and rendering options

## Environment Setup

1. **Python dependencies**:
   - Anthropic API client for Claude interaction (`pip install anthropic`)
   - PyYAML for configuration parsing (`pip install pyyaml`)
   - Required packages can be installed using:
     ```bash
     pip install anthropic pyyaml requests tqdm pillow
     ```

2. **Node.js dependencies**:
   - md2gslides npm package for Google Slides creation (`npm install -g md2gslides`)
   - Mermaid CLI for diagram generation (`npm install -g @mermaid-js/mermaid-cli`)
   - Install both with:
     ```bash
     npm install -g md2gslides @mermaid-js/mermaid-cli
     ```

3. **Credentials**:
   - Anthropic API key (set as environment variable ANTHROPIC_API_KEY)
     ```bash
     export ANTHROPIC_API_KEY="your-key-here"
     ```
   - Google API credentials (client_secret.json renamed to credentials.json)
     - Place in ~/.md2googleslides/client_id.json

4. **Directory Setup**:
   - Ensure an `images` directory exists for diagram outputs:
     ```bash
     mkdir -p images
     ```
   - The asset cache is stored in `~/.makeslides/assets` by default

## Guide Format Guidelines

Facilitator guides should follow this structure for optimal processing:

```markdown
# Title of Presentation

## Slide 1: Title Slide
- Title: Main Title
- Subtitle: Subtitle Text

## Slide 2: Content Slide
- Title: Slide Title
- Content: |
  * Bullet point 1
  * Bullet point 2
  * Bullet point 3

## Slide 3: Diagram Slide
- Title: Diagram Title
- Diagram Type: flowchart
- Diagram Content: |
  flowchart TD
    A[Start] --> B[Process]
    B --> C[End]

## Slide 4: Image Slide
- Title: Image Title
- Image URL: https://example.com/image.png
- Alt Text: Description of the image

## Slide 5: Two Column Layout
- Title: Two Column Layout
- Layout: TWO_COLUMNS
- Left Content: |
  * First left column item
  * Second left column item
- Right Content: |
  * First right column item
  * Second right column item

## Slide 6: Quote Slide
- Title: Important Quote
- Layout: QUOTE
- Quote: "The best way to predict the future is to create it."
- Attribution: Peter Drucker
```

## Workflow Details

### Recommended Automated Workflow

The most efficient workflow uses the new automated tools:

1. **Complete processing with magicSlide.sh and upload_and_fix_images.py**:
   ```bash
   ./magicSlide.sh guides/day2.md --stop-after=4
   python upload_and_fix_images.py slides_day2.md
   ```
   This handles the entire process from facilitator guide to Google Slides with proper image handling.

2. **Alternative: Use the all-in-one slidify-wrap.py**:
   ```bash
   python slidify-wrap.py guides/day2.md
   ```

### Detailed Process Steps

1. **Guide to JSON conversion**:
   - The facilitator guide markdown is parsed by Claude's structured thinking
   - Each slide section is converted to a JSON object with appropriate fields
   - Fields include title, content, layout, diagram content, image URLs, etc.
   - The enhanced prompt encourages varied slide layouts for more engaging presentations

2. **Diagram generation**:
   - Mermaid diagrams in the JSON are processed by diagrams_to_images.py
   - Each diagram is rendered to PNG and SVG using Mermaid CLI
   - Claude is used to fix any syntax errors in the diagrams
   - The JSON file is updated with local image paths
   - Images are named with clear identifiers: `{source_file}_slide{number}_{diagram_type}.png`

3. **JSON to markdown conversion**:
   - The processed JSON with diagram paths is converted to md2gslides markdown
   - Special formatting is applied based on slide layouts
   - Images are referenced with markdown syntax
   - The format-markdown.py tool is used to improve formatting of lists, agendas, and columns

4. **Image processing** (critical step):
   - Local images MUST have web URLs to display in Google Slides
   - **Automated solution**: Use upload_and_fix_images.py which:
     ```bash
     python upload_and_fix_images.py slides_day2.md
     ```
     - Automatically finds all diagrams and images in JSON and markdown
     - Uploads images to litterbox.catbox.moe 
     - Updates markdown with proper remote URLs
     - Generates Google Slides with all images visible
   - **Alternative solutions**:
     - direct_image_fixer.py: Simple approach to fix image URLs
     - embed_images.py: Embeds SVG content directly in markdown
     - auto_upload_images.py: Integrated with slidify-wrap.py workflow
   - **Manual processing**:
     - For single images: `./upload_temp_image.sh images/source_file_slideX_diagramtype.png`
     - For batch uploads: `./upload_all_images.sh [expiry_time]`
     - Manual update: `./update_image_urls.py slides_your_file.md`

5. **Google Slides generation**:
   - The markdown with proper image URLs is processed by md2gslides
   - The processed markdown creates a Google Slides presentation
   - Remote images are incorporated into the slides
   - The presentation URL is returned for access
   - This step is now integrated into upload_and_fix_images.py for a seamless experience

## Supported Slide Layouts

- **TITLE** - Title slide with optional subtitle
- **TITLE_AND_BODY** - Title with bulleted content (default)
- **SECTION_HEADER** - Section divider with title and optional subtitle
- **TWO_COLUMNS** - Title with two-column content layout
- **QUOTE** - Quote slide with attribution

## Supported Diagram Types

- **flowchart** - Directional flowcharts (TD, LR, RL, BT)
- **sequenceDiagram** - Sequence diagrams for interactions
- **classDiagram** - Class hierarchy diagrams
- **mindmap** - Mindmaps for hierarchical information
- **pie** - Pie charts for proportional data
- **timeline** - Timeline diagrams for sequential events

## Troubleshooting

1. **JSON Parsing Errors**:
   - Check the raw LLM response in debug files
   - Increase max_tokens in the Claude API call
   - Try processing the guide in smaller sections
   - If encountering 'list' object has no attribute 'get' error, use the updated `slidify-wrap.py` which handles both list and dictionary JSON structures

2. **Diagram Generation Errors**:
   - Ensure Mermaid syntax follows proper format
   - Check that diagram type is supported
   - Use proper case for diagram directions (e.g., "TD" for top-down)
   - Verify that Mermaid CLI is installed correctly
   - Use the enhanced `diagrams_to_images.py` which includes better error recovery

3. **Image Handling Issues**:
   - **IMPORTANT**: Images must have proper web URLs to work in Google Slides
   - Recommended solution: Use `upload_and_fix_images.py slides_your_file.md` which:
     - Automatically finds all images in the markdown and JSON
     - Uploads images to litterbox.catbox.moe with proper expiry settings
     - Updates markdown with proper remote URLs
     - Generates Google Slides with all images visible
   - Alternative options:
     - Use `direct_image_fixer.py` for a simpler approach
     - Try `embed_images.py` to embed SVG content directly in the markdown
     - Use `auto_upload_images.py` for integration with the workflow
   - For manual handling:
     - Use `./upload_temp_image.sh image.png` for individual files
     - Remember that litterbox.catbox.moe images expire (default is 24h)

4. **Google Slides Generation Issues**:
   - Make sure md2gslides is installed globally: `npm install -g md2gslides`
   - Check credentials in ~/.md2googleslides/client_id.json
   - For unsupported HTML in markdown, simplify to basic markdown syntax
   - Avoid complex HTML elements like div containers that md2gslides doesn't support
   - Use --fix-format flag to help with markdown formatting issues
   - If images don't appear in slides, use the `upload_and_fix_images.py` solution

5. **Markdown Formatting Issues**:
   - Use the enhanced `format-markdown.py` to improve formatting
   - For agenda slides with time entries, the new formatter will create proper spacing
   - For bullet points, the formatter now ensures proper line breaks before each item
   - For two-column layouts, content is now properly formatted with clear separation
   - NEVER use HTML div elements as they are not supported by md2gslides
   - For images, use standard markdown image syntax: `![alt text](image_url)`
   - For special layouts, use {.section} class notation (for section headers)

6. **Workflow Issues**:
   - If the workflow keeps failing at specific steps, try the new magicSlide.sh with --stop-after option:
     ```bash
     ./magicSlide.sh input_file.md --stop-after=4
     ```
   - This allows you to stop after step 4 (markdown generation) to process images with `upload_and_fix_images.py`
   - For issues with the 'images_dir' variable not being defined, use the updated `slidify-wrap.py`
   - If you need to debug specific steps, the modular approach lets you run each tool individually

## Example Files

The repository includes several example and template files:
- `simple_template.md` - Basic template for creating presentations
- `test_comprehensive.md` - Comprehensive test with various slide types
- `test_formatted.md` - Examples of improved formatting features
- `test_image_naming.md` - Examples of image naming conventions
- `test_columns.md` - Examples of two-column layouts
- `test_slide_variety.md` - Examples of varied slide layouts

## Development Commands

Here are the key commands for developing and maintaining the MakeSlides tool:

1. **Running Tests**:
   ```bash
   # Coming soon - test suite is under development
   ```

2. **Code Style and Linting**:
   ```bash
   # Format Python code
   black makeslides/ scripts/
   
   # Lint Python code
   flake8 makeslides/ scripts/
   ```

3. **Project Structure**:
   - `makeslides/` - Core Python package with modular components
     - `assets/` - Asset management utilities
     - `diagrams/` - Diagram rendering functionality
     - `guide/` - Guide parsing components
     - `markdown/` - Markdown generation and formatting
     - `slides/` - Google Slides generation tools
   - `scripts/` - Standalone utility scripts and tools
   - `config.yaml` - Main configuration file for Claude prompts

4. **Adding New Features**:
   - Extend core functionality in the appropriate module
   - Update the main workflow scripts (magicSlide.sh) to incorporate new steps
   - Follow the existing modular architecture pattern
   - Consider caching for performance improvements

## Recent Enhancements

The following improvements have been made to the MakeSlides tool:

1. **Improved Markdown Formatting**:
   - Enhanced agenda and schedule slide formatting
   - Better handling of bullet points and lists
   - Improved two-column layout rendering
   - Proper spacing and indentation throughout presentations

2. **Automated Image Processing**:
   - New `upload_and_fix_images.py` script for seamless image handling
   - Automatic image detection from JSON and markdown sources
   - Integrated image uploading to litterbox.catbox.moe
   - Automatic URL replacement in markdown files
   - One-step process to go from markdown to Google Slides with images

3. **Enhanced Workflow Options**:
   - Updated `magicSlide.sh` with --stop-after option
   - Improved error handling in `slidify-wrap.py`
   - Better JSON structure handling (both list and dictionary formats)
   - Multiple approaches to image handling for different use cases

4. **Updated Claude Prompt**:
   - Enhanced prompt to encourage varied slide layouts
   - Better guidance for two-column layouts
   - Improved structure for consistent JSON output

5. **Fixed Common Issues**:
   - Resolved 'images_dir' not defined error
   - Fixed JSON processing errors with different structures
   - Addressed markdown formatting issues with bullet points
   - Solved the critical issue of images not appearing in Google Slides