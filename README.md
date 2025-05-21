# MakeSlides

A CLI tool that uses AI to convert training facilitator guides into Google Slides presentations.

## Features

- 🤖 Uses Claude AI to process facilitator guides into structured JSON
- 🎯 Creates professional Google Slides presentations with consistent formatting
- 📊 Generates Mermaid diagrams for flowcharts, mindmaps, and other visualizations
- 🖼️ Integrates images with automatic uploading and hosting
- 📝 Preserves facilitator notes in slide speaker notes
- 🔄 Validates and repairs diagrams automatically
- 📋 Creates CSV overviews of presentations
- 🎭 Supports varied slide layouts to create visual interest

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   npm install
   ```
3. Set up your environment:
   - Create a `.env` file with your Anthropic API key:
     ```
     ANTHROPIC_API_KEY=your-key-here
     ```
   - Rename the client secret JSON file to `credentials.json` for Google API access
   - Install the Mermaid CLI:
     ```
     npm install -g @mermaid-js/mermaid-cli
     ```

## Usage

### All-in-One Solution

The easiest way to create slides is with the `magicSlide.sh` script:

```bash
./magicSlide.sh path/to/guide.md
```

This will:
1. Convert your facilitator guide to JSON
2. Generate diagrams for all slides
3. Create a CSV overview
4. Convert to markdown
5. Generate Google Slides

For even simpler usage with automatic image handling:

```bash
# Generate markdown (steps 1-4)
./magicSlide.sh path/to/guide.md --stop-after=4

# Upload images and create presentation
python upload_and_fix_images.py slides_filename.md
```

### Individual Steps

If you prefer to run each step manually:

#### 1. Processing Facilitator Guides

Convert a facilitator guide to JSON format:

```bash
python guide_to_json.py path/to/guide.md
```

This will generate a `slides_<filename>.json` file with the structured content.

#### 2. Processing Diagrams

Generate images from Mermaid diagrams in your JSON file:

```bash
python diagrams_to_images.py slides_<filename>.json
```

This will:
1. Find all diagram content in the JSON
2. Render them using Mermaid CLI
3. Save the images in the `images/` directory
4. Update the JSON with the image paths

#### 3. Converting JSON to Markdown

Convert the processed JSON to markdown format:

```bash
python json_to_markdown.py slides_<filename>.json
```

This creates a `slides_<filename>.md` file formatted for use with Google Slides.

#### 4. Building Google Slides

Generate Google Slides from the markdown:

```bash
python build_with_md2gslides.py slides_<filename>.md --fix-format --use-fileio
```

### Image Handling

**Important**: md2gslides **requires** images to be hosted online. Local image paths will not work, even with the `--use-fileio` option.

#### Automated Solution (Recommended)

The simplest approach is to use our automatic image uploader:

```bash
python upload_and_fix_images.py slides_your_file.md
```

This script will:
1. Find all images referenced in your markdown and JSON
2. Upload them to litterbox.catbox.moe
3. Update your markdown with the remote URLs
4. Generate the Google Slides presentation

#### Alternative Approaches

You can also use our other image handling tools:

##### 1. Direct Image Fixer

```bash
python direct_image_fixer.py slides_your_file.md
```

A simpler script that just handles image upload and URL replacement.

##### 2. Manual Image Upload

Upload individual images:

```bash
./upload_temp_image.sh images/your_file_slideX_diagramtype.png [expiry_time]
```

Where expiry_time can be 1h, 12h, 24h, or 72h (default: 24h).

##### 3. Batch Upload

Upload all images at once:

```bash
./upload_all_images.sh [expiry_time]
```

The script will:
1. Upload all PNG files in the images directory to litterbox.catbox.moe
2. Create an `image_urls.txt` file mapping local paths to remote URLs
3. Show a summary of the uploads

##### 4. Updating Markdown with Image URLs

After uploading images, update your markdown:

```bash
./update_image_urls.py slides_your_file.md
```

This script will:
1. Read the `image_urls.txt` mapping file 
2. Replace all local image references in your markdown with remote URLs
3. Show a summary of replaced references

**Note**: litterbox.catbox.moe hosts images temporarily (they expire after the specified time). For permanent presentations, consider a more permanent hosting solution.

## Workflow Options

### Recommended Workflow (Easiest)

1. Create a facilitator guide markdown file with structured sections for slides
2. Process with magicSlide.sh to generate markdown:
   ```bash
   ./magicSlide.sh your_guide.md --stop-after=4
   ```
3. Use the automated image handling and slides generation:
   ```bash
   python upload_and_fix_images.py slides_your_guide.md
   ```

### Manual Workflow (Traditional)

1. Create a facilitator guide markdown file with structured sections for slides
2. Process the guide with `guide_to_json.py` to create JSON
3. Generate diagrams with `diagrams_to_images.py`
4. Convert to markdown with `json_to_markdown.py`
5. Upload images with `upload_all_images.sh`
6. Update markdown with URLs using `update_image_urls.py`
7. Generate Google Slides with `build_with_md2gslides.py`

## Guide Format

Facilitator guides should follow this structure:

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
```

## Configuration

- **Prompts**: Stored in YAML format in the `prompts/` directory
  - `facilitator-guide-to-json.yaml` - Controls how Claude processes guides

- **Diagrams**: Configuration in `mermaid-config.json`
  - Diagrams are generated using Mermaid CLI
  - Supports flowcharts, mindmaps, sequence diagrams, etc.

- **Storage**: Local images stored in the `images/` directory

## Troubleshooting

### Missing Images in Slides

This is the most common issue. If your slides don't show images:

1. **Use the automated image handling**:
   ```bash
   python upload_and_fix_images.py slides_your_file.md
   ```
   This script will find, upload, and properly reference all images.

2. **Check image references** in your markdown file:
   - Images must use URLs, not local paths
   - Check that URLs are accessible in your browser
   - Use the `update_image_urls.py` script to fix references

3. **Verify image hosting**:
   - Make sure the images were successfully uploaded to litterbox.catbox.moe
   - Check if any images have expired (default 24h lifespan)
   - Try re-uploading with `upload_all_images.sh`

### Other Common Issues

- **JSON Parsing Errors**:
  - Check the raw LLM response in the debug directory
  - Increase `max_tokens` in the Claude API call
  - Try splitting your guide into smaller sections

- **Diagram Generation Errors**:
  - Ensure diagram syntax follows the Mermaid specification
  - Use proper case for diagram directions (e.g., "TD" for top-down)
  - Simplify complex diagrams (15 nodes or fewer is ideal)

- **Slide Layout Issues**:
  - Use the new format-markdown.py script: `python format-markdown.py slides_your_file.md`
  - For two-column layouts, use the {.column} marker as shown in the examples
  - Avoid HTML elements - md2gslides only supports limited markdown

- **Google Slides Generation**:
  - Verify Google API credentials in ~/.md2googleslides/client_id.json
  - Make sure md2gslides is installed: `npm install -g md2gslides`
  - Run with the --debug flag to see more information about errors

## Example Files

The repository includes several example files:
- `simple_template.md` - A basic template for creating presentations
- `test_comprehensive.md` - A comprehensive test with various slide types

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

ISC License