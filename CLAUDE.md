# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MakeSlides** is an AI-powered CLI tool that transforms training facilitator guides into professional Google Slides presentations through an intelligent multi-stage pipeline.

### Core Workflow

1. **AI-Powered Parsing**: Uses Claude API to analyze markdown facilitator guides and convert them to structured JSON with intelligent layout selection
2. **Diagram Generation**: Renders Mermaid diagrams to images with automatic syntax validation and error correction
3. **Markdown Conversion**: Transforms JSON to md2gslides-compatible markdown with rich layout support
4. **Image Management**: Automatically uploads local images to cloud hosting and updates references
5. **Slides Generation**: Creates Google Slides presentations via md2gslides npm package

### Key Features

- **Intelligent Layout Selection**: Claude AI analyzes content semantics to choose appropriate slide layouts
- **Automatic Diagram Repair**: AI-assisted fixing of Mermaid syntax errors with fallback mechanisms
- **Robust Error Handling**: Retry logic, exponential backoff, and graceful degradation throughout
- **Modular Architecture**: Each component can run independently or as part of automated workflow
- **Batch Processing**: Support for processing multiple guides in a single directory
- **Asset Management**: Caching system to avoid regenerating identical diagrams

## Architecture

The codebase consists of these main components:

1. **Guide to JSON Processor (`guide/parser.py`)** - Converts facilitator guides to structured JSON:
   - Uses Claude API with tool calling for structured output
   - Extracts slide content, titles, diagrams, and metadata
   - Normalizes output and validates JSON formatting
   - Applies layout mappings and defaults
   - Supports both single file and batch directory processing

2. **Diagram Generator (`diagrams/renderer.py`)** - Creates diagrams from Mermaid syntax:
   - Validates and repairs common Mermaid syntax issues
   - Generates PNG and SVG diagrams from Mermaid specifications
   - Uses Claude API to fix syntax errors intelligently
   - Handles error cases with fallback diagrams
   - Implements retry logic with exponential backoff
   - Creates hash-based caching to avoid duplicate rendering

3. **Markdown Generator (`markdown/generator.py`)** - Converts JSON to markdown for slide creation:
   - Processes JSON slide data into md2gslides-compatible markdown
   - Handles diagrams and images with smart path resolution
   - Creates content formatted for various slide layouts
   - Supports SVG embedding and image block formatting
   - Intelligent content splitting for two-column layouts

4. **Slides Generator (`slides/builder.py`)** - Creates Google Slides presentations:
   - Uses md2gslides npm package to create presentations
   - Validates markdown content before generation
   - Handles image and diagram embedding
   - Provides detailed logging and error handling
   - Supports appending to existing presentations

5. **Asset Manager (`assets/asset_manager.py`)** - Manages image and diagram assets:
   - Caches diagrams to avoid regeneration (content hash-based)
   - Provides consistent file naming conventions
   - Handles storage and retrieval of assets
   - Default cache location: `~/.makeslides/assets`

6. **Image Processing Tools**:
   - **`scripts/upload_and_fix_images.py`** - Comprehensive image processing solution:
     - Finds images referenced in JSON and markdown
     - Uploads images to temporary hosting service (litterbox.catbox.moe)
     - Updates markdown with remote image URLs
     - Generates Google Slides with properly displayed images
     - Implements retry logic for upload resilience
   - **`scripts/direct_image_fixer.py`** - Direct approach to image URL replacement
   - **`markdown/embed_images.py`** - Alternative solution that embeds SVG content directly

7. **Workflow Wrapper (`scripts/magicSlide.sh`)** - Combines all processing steps:
   - Manages the complete workflow from guide to presentation
   - Handles both single files and directories (batch mode)
   - Creates and verifies required directories
   - Coordinates all processing stages with progress tracking
   - Provides extensive command-line options for customization
   - Supports step-by-step execution (--start-step, --stop-after)
   - Verifies dependencies and credentials

## Commands

### Recommended Workflow (Automated)

The most efficient workflow uses the magicSlide.sh script with the image processing tools:

1. **Complete workflow with automatic image processing**:
   ```bash
   ./magicSlide.sh guides/day2.md --stop-after=4
   python upload_and_fix_images.py slides_day2.md
   ```
   This processes the guide, creates markdown, uploads all images, and generates Google Slides with properly displayed images.

2. **Full automated workflow (all 5 steps)**:
   ```bash
   ./magicSlide.sh guides/day2.md
   ```
   This runs all steps from guide to final Google Slides presentation.

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

4. **Process images for Google Slides compatibility**:
   ```bash
   python upload_and_fix_images.py slides_day2.md
   ```
   This finds, uploads, and updates image references in the markdown before creating the slides.

5. **Alternative image processing options**:
   - For direct image fixing:
     ```bash
     python direct_image_fixer.py slides_day2.md
     ```
   - For manual image uploads:
     ```bash
     ./upload_temp_image.sh path/to/image.png [expiry_time]
     ```
     Where expiry_time can be 1h, 12h, 24h, or 72h (default: 24h).

6. **Manual Google Slides generation** (if not using automated tools):
   ```bash
   python build_with_md2gslides.py slides_day2.md --fix-format --use-fileio
   ```
   This creates a Google Slides presentation and returns the URL.

## Configuration Files

1. **config.yaml** - Contains the prompt template for Claude to process facilitator guides:
   - Controls the prompt for LLM processing
   - Defines layout mappings (title, section, content, columns, etc.)
   - Sets slide defaults
   - Highly customizable for different presentation styles

2. **mermaid-config.json** - Configuration for Mermaid diagram generation:
   - Defines styling for diagrams
   - Sets default theme and rendering options

## Environment Setup

### 1. Python Dependencies

```bash
# Install package in development mode
pip install -e .

# Or install dependencies manually
pip install anthropic pyyaml requests tqdm pillow
```

### 2. Node.js Dependencies

```bash
# Install md2gslides and mermaid-cli
npm install -g md2gslides @mermaid-js/mermaid-cli
```

### 3. Credentials

**Anthropic API Key**:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**Google API Credentials**:
- Create OAuth 2.0 credentials at https://console.developers.google.com
- Enable Google Slides API
- Download credentials JSON and save as:
  - `~/.md2googleslides/client_id.json`

### 4. Directory Setup

```bash
# Create images directory
mkdir -p images

# Asset cache (created automatically)
# Default location: ~/.makeslides/assets
```

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

### Detailed Process Steps

1. **Guide to JSON conversion**:
   - The facilitator guide markdown is parsed by Claude with extended thinking
   - Each slide section is converted to a JSON object with appropriate fields
   - Fields include title, content, layout, diagram content, image URLs, facilitator notes, timing
   - The enhanced prompt encourages varied slide layouts for more engaging presentations
   - Uses tool calling API for structured output

2. **Diagram generation**:
   - Mermaid diagrams in the JSON are processed by diagrams_to_images.py
   - Each diagram is rendered to PNG and SVG using Mermaid CLI
   - Claude is used to fix any syntax errors in the diagrams (with retry logic)
   - The JSON file is updated with local image paths
   - Images are named with clear identifiers: `{source_file}_slide{number}_{diagram_type}.png`
   - Fallback mechanisms create basic diagrams if rendering fails

3. **JSON to markdown conversion**:
   - The processed JSON with diagram paths is converted to md2gslides markdown
   - Special formatting is applied based on slide layouts
   - Images are referenced with markdown syntax
   - Supports multiple layout templates (title, section, columns, quote, etc.)

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
   - **Important**: litterbox.catbox.moe images expire (default is 24h)

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
- **TWO_COLUMNS** / **TITLE_AND_TWO_COLUMNS** - Title with two-column content layout
- **QUOTE** - Quote slide with attribution
- **MAIN_POINT** - Emphasize a key takeaway (large text)
- **BIG_NUMBER** - Display statistics or metrics prominently
- **CAPTION** - Image with caption
- **BLANK** - Full-screen background image

## Supported Diagram Types

- **flowchart** - Directional flowcharts (TD, LR, RL, BT)
- **sequenceDiagram** - Sequence diagrams for interactions
- **classDiagram** - Class hierarchy diagrams
- **mindmap** - Mindmaps for hierarchical information
- **pie** - Pie charts for proportional data
- **timeline** - Timeline diagrams for sequential events
- **quadrantChart** - Quadrant charts for categorization
- **stateDiagram-v2** - State diagrams
- **gantt** - Gantt charts for project timelines
- **journey** - User journey diagrams

## Development Commands

### Installation & Setup

```bash
# Install package in development mode
pip install -e .

# Install with all dependencies
pip install anthropic pyyaml requests tqdm pillow

# Install Node.js dependencies
npm install -g md2gslides @mermaid-js/mermaid-cli
```

### Running Tests

```bash
# Test suite is under development
# TODO: Add pytest configuration and test cases
```

### Code Quality

```bash
# Format Python code
black makeslides/ scripts/

# Lint Python code
flake8 makeslides/ scripts/

# Type checking (when type hints are added)
mypy makeslides/
```

### Project Structure

```
makeslides/
├── makeslides/              # Core Python package
│   ├── assets/             # Asset management (caching, storage)
│   ├── diagrams/           # Mermaid diagram rendering
│   ├── guide/              # Facilitator guide parsing
│   ├── markdown/           # Markdown generation & formatting
│   └── slides/             # Google Slides generation
├── scripts/                # Utility scripts
│   ├── magicSlide.sh      # Main workflow orchestrator
│   ├── upload_and_fix_images.py  # Image hosting solution
│   └── direct_image_fixer.py     # Alternative image fixer
├── config.yaml             # Claude prompt configuration
├── setup.py               # Package configuration
└── cli.py                 # Command-line interface
```

### Adding New Features

1. **Extend Core Modules**: Add functionality in appropriate module (guide/, diagrams/, etc.)
2. **Update Workflow**: Modify magicSlide.sh to incorporate new steps
3. **Follow Patterns**: Use existing error handling, logging, and retry patterns
4. **Consider Caching**: Leverage asset manager for performance
5. **Update Documentation**: Add to CLAUDE.md, README.md, and docstrings

### Architecture Principles

- **Separation of Concerns**: Each module has single, clear responsibility
- **Error Resilience**: Retry logic with exponential backoff for external services
- **Graceful Degradation**: System continues with fallbacks when components fail
- **Configuration-Driven**: Behavior controlled via config.yaml, not hardcoded
- **CLI-First**: All features accessible via command-line with rich options

## Troubleshooting

### 1. JSON Parsing Errors

- Check the raw LLM response in debug files
- Increase max_tokens in the Claude API call (currently 16,000)
- Try processing the guide in smaller sections
- If encountering structure errors, check that config.yaml is properly formatted
- Use `--force-json` flag to attempt extraction from malformed responses

### 2. Diagram Generation Errors

- Ensure Mermaid syntax follows proper format
- Check that diagram type is supported (see list above)
- Use proper case for diagram directions (e.g., "TD" for top-down)
- Verify that Mermaid CLI is installed correctly: `mmdc --version`
- The system will attempt to fix syntax errors automatically using Claude
- Claude-assisted fixing requires ANTHROPIC_API_KEY to be set
- Keep diagrams simple (15 nodes or fewer recommended)

### 3. Image Handling Issues

- **IMPORTANT**: Images must have proper web URLs to work in Google Slides
- **Recommended solution**: Use `upload_and_fix_images.py slides_your_file.md` which:
  - Automatically finds all images in the markdown and JSON
  - Uploads images to litterbox.catbox.moe with proper expiry settings
  - Updates markdown with proper remote URLs
  - Generates Google Slides with all images visible
- **Known limitation**: litterbox.catbox.moe images expire (default is 24h)
- For production use, consider implementing permanent hosting (S3, Cloudinary, etc.)

### 4. Google Slides Generation Issues

- Make sure md2gslides is installed globally: `npm install -g md2gslides`
- Check credentials in `~/.md2googleslides/client_id.json`
- For unsupported HTML in markdown, simplify to basic markdown syntax
- Avoid complex HTML elements like div containers (not supported by md2gslides)
- Use `--fix-format` flag to help with markdown formatting issues
- If images don't appear in slides, use the `upload_and_fix_images.py` solution
- Run with `--debug` flag to see detailed output

### 5. Markdown Formatting Issues

- NEVER use HTML div elements (not supported by md2gslides)
- For images, use standard markdown image syntax: `![alt text](image_url)`
- For special layouts, use class notation: `{.section}`, `{.big}`, `{.column}`
- Use `--prefer-svg` flag to embed SVG diagrams directly
- For two-column layouts, content is automatically split or can use pipe separator: `left | right`

### 6. Workflow Issues

- If the workflow keeps failing at specific steps, try with `--stop-after` option:
  ```bash
  ./magicSlide.sh input_file.md --stop-after=4
  ```
- To resume from a specific step:
  ```bash
  ./magicSlide.sh input_file.md --start-step=3
  ```
- Use `--debug` flag for verbose output and validation
- Check progress file: `.magicslide_progress` in working directory

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
   - Updated `magicSlide.sh` with --stop-after and --start-step options
   - Progress tracking to resume failed workflows
   - Better JSON structure handling (both list and dictionary formats)
   - Multiple approaches to image handling for different use cases
   - Asset management with caching to avoid redundant diagram generation

4. **Updated Claude Prompt**:
   - Enhanced prompt to encourage varied slide layouts
   - Better guidance for two-column layouts
   - Improved structure for consistent JSON output
   - Extended thinking mode for better content analysis

5. **Fixed Common Issues**:
   - Resolved JSON processing errors with different structures
   - Addressed markdown formatting issues with bullet points
   - Solved the critical issue of images not appearing in Google Slides
   - Improved error messages and debugging output

## Future Evolution Ideas

### Potential Enhancements

1. **Multi-Format Output Support**: Export to PowerPoint, PDF, reveal.js, Marp
2. **Permanent Image Hosting**: Integration with S3, Cloudinary, or self-hosted solutions
3. **Interactive Web Editor**: GUI for reviewing and editing generated presentations
4. **Quality Analytics**: Readability scores, accessibility checks, pacing analysis
5. **Template Library**: Reusable templates and content marketplace
6. **Offline Mode**: Local-first workflow without external API dependencies
7. **Testing Suite**: Comprehensive unit and integration tests
8. **Type Safety**: Full type hints throughout codebase with mypy validation
9. **Multilingual Support**: Automatic translation for international presentations
10. **Theme Customization**: Custom branding, colors, and fonts
