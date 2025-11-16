# MakeSlides

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](https://github.com/bilalghalib/makeslides)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-ISC-green.svg)](LICENSE)

**AI-powered CLI tool that converts training facilitator guides into professional Google Slides presentations.**

Transform your markdown facilitator guides into engaging, professionally formatted presentations with intelligent layout selection, automatic diagram generation, and seamless image management—all powered by Claude AI.

## Features

- 🤖 **AI-Powered Parsing**: Uses Claude AI to intelligently analyze facilitator guides and structure content
- 🎯 **Smart Layout Selection**: Automatically chooses optimal slide layouts based on content semantics
- 📊 **Automatic Diagram Generation**: Creates Mermaid diagrams (flowcharts, mindmaps, timelines, etc.) with error correction
- 🖼️ **Seamless Image Management**: Automatically uploads and hosts images for Google Slides compatibility
- 📝 **Rich Slide Layouts**: Supports 10+ layout types (title, section, columns, quote, big number, etc.)
- 🔄 **Robust Error Handling**: Retry logic with exponential backoff and graceful degradation
- 📋 **Batch Processing**: Process multiple guides in a directory simultaneously
- 💾 **Asset Caching**: Intelligent caching to avoid regenerating identical diagrams
- 🎭 **Visual Variety**: Encourages varied, engaging presentations with two-column layouts and visual elements
- 🔧 **Modular Architecture**: Each component can run independently for maximum flexibility

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/bilalghalib/makeslides.git
cd makeslides

# Install Python dependencies
pip install -e .

# Install Node.js dependencies
npm install -g md2gslides @mermaid-js/mermaid-cli
```

### Setup

1. **Set up Anthropic API key** (for Claude AI):
   ```bash
   export ANTHROPIC_API_KEY="your-key-here"
   ```

2. **Configure Google Slides API**:
   - Go to [Google Cloud Console](https://console.developers.google.com)
   - Create a project and enable Google Slides API
   - Create OAuth 2.0 credentials (Desktop Application)
   - Download the JSON file and save as `~/.md2googleslides/client_id.json`

### Basic Usage

```bash
# One-command solution (all steps)
./magicSlide.sh guides/your_guide.md

# Or step-by-step with image handling
./magicSlide.sh guides/your_guide.md --stop-after=4
python upload_and_fix_images.py slides_your_guide.md
```

## Usage

### All-in-One Solution

The easiest way to create slides is with the `magicSlide.sh` script:

```bash
# Full workflow (guide → JSON → diagrams → markdown → slides)
./magicSlide.sh path/to/guide.md

# Stop before slides generation (useful for image processing)
./magicSlide.sh path/to/guide.md --stop-after=4
python upload_and_fix_images.py slides_filename.md

# Batch processing (process entire directory)
./magicSlide.sh guides/ --title-prefix="Training: "
```

### Individual Steps

For more control, run each step separately:

#### 1. Convert Guide to JSON

```bash
python guide_to_json.py guides/day2.md
# Creates: slides_day2.json
```

#### 2. Generate Diagrams

```bash
python diagrams_to_images.py slides_day2.json
# Creates diagrams in: images/
```

#### 3. Convert to Markdown

```bash
python json_to_markdown.py slides_day2.json
# Creates: slides_day2.md
```

#### 4. Upload Images & Generate Slides

```bash
python upload_and_fix_images.py slides_day2.md
# Uploads images, updates markdown, creates Google Slides
```

### Advanced Options

```bash
# Use different Claude model
./magicSlide.sh guide.md --model=claude-3-7-sonnet-20250219

# Debug mode with verbose output
./magicSlide.sh guide.md --debug

# Start from specific step (e.g., resume from step 3)
./magicSlide.sh guide.md --start-step=3

# Custom asset cache directory
./magicSlide.sh guide.md --asset-dir=/path/to/cache

# Verify installation before running
./magicSlide.sh guide.md --verify-npm
```

## Guide Format

Facilitator guides should follow this markdown structure:

```markdown
# Training Title

## Slide 1: Welcome
- Title: Welcome to Solar Energy Training
- Subtitle: Mosul, Iraq - 2024
- Layout: title

## Slide 2: Learning Objectives
- Title: Today's Learning Objectives
- Content: |
  * Understand solar panel components
  * Learn installation best practices
  * Master safety protocols
  * Practice troubleshooting techniques
- Layout: content

## Slide 3: Installation Process
- Title: Installation Process Flow
- Diagram Type: flowchart
- Diagram Content: |
  flowchart TD
    A[Site Assessment] --> B[Panel Mounting]
    B --> C[Electrical Connection]
    C --> D[Testing]
    D --> E[Commissioning]
- Layout: content

## Slide 4: Key Takeaway
- Title: Safety First!
- Content: Always follow proper safety protocols
- Layout: main_point
```

## Supported Features

### Slide Layouts

- **TITLE**: Title slide with subtitle
- **SECTION_HEADER**: Section divider
- **TITLE_AND_BODY**: Content with bullet points (default)
- **TWO_COLUMNS**: Side-by-side content or content + image
- **QUOTE**: Emphasized quote with attribution
- **MAIN_POINT**: Large text for key takeaways
- **BIG_NUMBER**: Statistics or metrics
- **CAPTION**: Image with caption
- **BLANK**: Full-screen background image

### Diagram Types

- **flowchart**: Process flows (TD, LR, RL, BT)
- **mindmap**: Hierarchical information
- **pie**: Proportional data
- **timeline**: Sequential events
- **sequenceDiagram**: Interactions between entities
- **classDiagram**: Class relationships
- **quadrantChart**: 2x2 categorization
- **gantt**: Project timelines
- **journey**: User journey maps
- **stateDiagram-v2**: State transitions

## Configuration

### config.yaml

Controls Claude AI's behavior when parsing guides:

```yaml
prompt_template: "{{content}}"  # Main prompt template
layout_mappings:
  title: "TITLE"
  section: "SECTION_HEADER"
  content: "TITLE_AND_BODY"
  columns: "TITLE_AND_TWO_COLUMNS"
  # ... more mappings
slide_defaults:
  chart_type: null
  image_url: null
```

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="your-anthropic-key"

# Optional
export MAKESLIDES_ASSET_DIR="~/.makeslides/assets"
```

## Troubleshooting

### Images Don't Appear in Slides

**Solution**: Images must be hosted online for Google Slides.

```bash
# Automated solution (recommended)
python upload_and_fix_images.py slides_your_file.md
```

**Note**: Images are uploaded to litterbox.catbox.moe and expire after 24h by default. For production presentations, consider implementing permanent hosting (S3, Cloudinary, etc.).

### Diagram Generation Fails

- Ensure Mermaid CLI is installed: `npm install -g @mermaid-js/mermaid-cli`
- Verify syntax with [Mermaid Live Editor](https://mermaid.live)
- The system will auto-fix most errors using Claude AI
- Keep diagrams simple (≤15 nodes recommended)

### JSON Parsing Errors

- Check that guide follows the expected format
- Use `--force-json` flag to attempt extraction from malformed responses
- Increase max_tokens if content is truncated
- Process large guides in smaller sections

### Google Slides Generation Fails

- Verify credentials: `~/.md2googleslides/client_id.json`
- Check md2gslides installation: `md2gslides --version`
- Use `--fix-format` flag for markdown validation
- Run with `--debug` for detailed error messages

## Architecture

```
makeslides/
├── makeslides/              # Core Python package
│   ├── assets/             # Asset caching & management
│   ├── diagrams/           # Mermaid rendering
│   ├── guide/              # AI-powered parsing
│   ├── markdown/           # Markdown generation
│   └── slides/             # Google Slides creation
├── scripts/                # Workflow automation
│   ├── magicSlide.sh      # Main orchestrator
│   └── upload_and_fix_images.py  # Image management
├── config.yaml             # Prompt configuration
└── setup.py               # Package setup
```

### Key Principles

- **Separation of Concerns**: Each module has a single, clear responsibility
- **Error Resilience**: Retry logic with exponential backoff for all external services
- **Graceful Degradation**: System continues with fallbacks when components fail
- **Configuration-Driven**: Behavior controlled via config files, not hardcoded
- **CLI-First**: All features accessible via command-line

## Code Review Summary

### What This Code Does

MakeSlides is an intelligent automation tool that transforms training facilitator guides into professional Google Slides presentations through a 5-stage AI-powered pipeline:

1. **Parsing**: Claude AI analyzes markdown guides and structures content into JSON
2. **Diagram Rendering**: Mermaid diagrams are generated as PNG/SVG with auto-correction
3. **Markdown Generation**: JSON is converted to md2gslides-compatible markdown
4. **Image Processing**: Local images are uploaded to cloud hosting and references updated
5. **Slides Generation**: Final Google Slides presentation is created

### 5 Major Pros

1. **AI-Powered Intelligence**: Claude AI provides exceptional flexibility in parsing varied input formats, intelligently selecting layouts, and automatically fixing diagram syntax errors
2. **Robust Error Handling**: Comprehensive retry logic with exponential backoff, fallback mechanisms, and graceful degradation throughout the pipeline
3. **Modular Architecture**: Clean separation of concerns makes the codebase maintainable, testable, and allows independent use of components
4. **Rich Configuration**: Extensive customization via config.yaml without code changes, adaptable to different presentation styles and contexts
5. **Comprehensive Workflow Management**: The magicSlide.sh script offers step-by-step execution, progress tracking, batch processing, and extensive CLI options

### 5 Major Cons

1. **External Service Dependencies**: Critical reliance on Anthropic API, litterbox.catbox.moe, Google Slides API, and md2gslides creates fragility
2. **Limited Offline Capability**: Requires internet for multiple operations with no offline or local-first workflow option
3. **Tight md2gslides Coupling**: Markdown generation specifically tailored to md2gslides' limited syntax, difficult to migrate to other tools
4. **Temporary Image Hosting**: Images expire (default 24h), presentations become broken, no permanent production solution
5. **Incomplete Testing**: No unit tests, integration tests, or comprehensive API documentation in the codebase

### 5 Evolution Opportunities

1. **Multi-Format Output**: Add support for PowerPoint (python-pptx), PDF, reveal.js, Marp, Beamer (LaTeX) with format-specific optimizations
2. **Permanent Image Management**: Implement S3, Cloudinary, or self-hosted solutions with optimization, caching, and search integration
3. **Interactive Web Editor**: Build GUI for reviewing/editing presentations with side-by-side comparison, drag-and-drop, and collaborative features
4. **Advanced Analytics**: Add readability analysis, pacing metrics, accessibility validation, and quality recommendations
5. **Template Marketplace**: Create library of reusable templates, content blocks, theme customization, and community sharing platform

## Examples

See the repository for example files:
- `simple_template.md` - Basic template
- `test_comprehensive.md` - Various slide types
- `test_slide_variety.md` - Layout examples

## Development

### Contributing

```bash
# Format code
black makeslides/ scripts/

# Lint
flake8 makeslides/ scripts/

# Type checking (when implemented)
mypy makeslides/
```

### Testing

```bash
# Test suite under development
# TODO: Add pytest configuration
```

## Roadmap

- [ ] Comprehensive test suite (unit & integration)
- [ ] Full type hints with mypy validation
- [ ] Permanent image hosting integration (S3, Cloudinary)
- [ ] Multi-format export (PowerPoint, PDF, reveal.js)
- [ ] Web-based presentation editor
- [ ] Accessibility checker and quality metrics
- [ ] Template library and marketplace
- [ ] Multilingual support
- [ ] Offline mode with local LLM support

## License

ISC License - see LICENSE file for details.

## Credits

Built with:
- [Anthropic Claude](https://www.anthropic.com/) - AI-powered content analysis
- [md2gslides](https://github.com/googleworkspace/md2googleslides) - Google Slides generation
- [Mermaid](https://mermaid.js.org/) - Diagram rendering

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check [CLAUDE.md](CLAUDE.md) for detailed documentation
- Review examples in the repository

---

**Made with ❤️ for training facilitators everywhere**
