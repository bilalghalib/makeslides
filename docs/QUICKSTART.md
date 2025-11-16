# Quick Start Guide - Phase 1 & 2 Features

## 🚀 New Export Formats

MakeSlides now supports multiple export formats beyond Google Slides!

### Installation

```bash
# Install with new dependencies
pip install -e .

# Or install individually
pip install python-pptx  # For PPTX export
pip install anthropic pyyaml requests pillow  # Core dependencies
```

---

## 📊 Export to PowerPoint (PPTX)

**Best for**: Offline editing, corporate environments, full control

### Quick Example

```bash
# Process guide to JSON
python guide_to_json.py guides/my_training.md

# Generate diagrams
python diagrams_to_images.py slides_my_training.json

# Export to PowerPoint
python export_presentation.py slides_my_training.json --format pptx
```

**Benefits**:
- ✅ **No internet required** - Images embedded in file
- ✅ **Offline editing** - Full PowerPoint features
- ✅ **Corporate compatibility** - Works everywhere
- ✅ **Professional layouts** - 9 different slide layouts

### Output

- **File**: `my_training.pptx`
- **Compatible with**: PowerPoint, LibreOffice, Google Slides, Keynote

---

## 🌐 Export to reveal.js (HTML)

**Best for**: Web presentations, online training, interactive slides

### Quick Example

```bash
# Export to reveal.js
python export_presentation.py slides_my_training.json --format revealjs --theme sky

# Open in browser
open my_training_revealjs.html
```

**Themes Available**:
- `black` (default) - Dark background
- `white` - Light background
- `league` - Gray background
- `beige` - Beige background
- `sky` - Blue gradient
- `night` - Dark with orange highlights
- `serif` - Serif fonts
- `simple` - Minimalist
- `solarized` - Solarized colors
- `moon` - Dark blue

**Benefits**:
- ✅ **Self-contained HTML** - Single file, works offline
- ✅ **Beautiful animations** - Smooth transitions
- ✅ **Keyboard shortcuts** - Arrow keys, ESC for overview
- ✅ **Speaker notes** - Press 'S' for notes view
- ✅ **Mobile friendly** - Touch gestures

### reveal.js Features

**Keyboard Shortcuts**:
- `→` / `←` - Next/previous slide
- `ESC` - Slide overview
- `S` - Speaker notes view
- `F` - Fullscreen
- `B` - Pause (black screen)
- `?` - Help menu

**URL Parameters**:
```bash
# Open with specific slide
my_training_revealjs.html#/3

# Print to PDF
my_training_revealjs.html?print-pdf
```

---

## 🖼️ Imgur Image Hosting

**Replaces**: Temporary litterbox.catbox.moe hosting
**New**: Permanent, free Imgur hosting

### Upload Single Image

```bash
python -m makeslides.images.imgur_uploader images/diagram.png
```

### Upload Directory

```bash
python -m makeslides.images.imgur_uploader images/ --directory --pattern "*.png"
```

### Use in Python

```python
from makeslides.images.imgur_uploader import upload_image

# Upload and get permanent URL
url = upload_image("images/my_diagram.png")
print(url)  # https://i.imgur.com/xxxxx.png
```

**Benefits**:
- ✅ **Free unlimited uploads** - No cost
- ✅ **Permanent hosting** - Images don't expire
- ✅ **Reliable CDN** - Fast worldwide
- ✅ **No authentication needed** - Anonymous uploads OK

---

## 🎯 Complete Workflow Examples

### Example 1: PowerPoint for Corporate Training

```bash
# 1. Create facilitator guide (markdown)
cat > guides/onboarding.md << 'EOF'
# Employee Onboarding

## Slide 1: Welcome
- Title: Welcome to Our Company!
- Content: Let's get started with your journey

## Slide 2: Company Values
- Title: Our Core Values
- Content: |
  * Innovation
  * Integrity
  * Collaboration
  * Excellence
EOF

# 2. Process to JSON
python guide_to_json.py guides/onboarding.md

# 3. Generate diagrams (if any)
python diagrams_to_images.py slides_onboarding.json

# 4. Export to PowerPoint
python export_presentation.py slides_onboarding.json --format pptx

# Output: onboarding.pptx (ready to edit offline!)
```

### Example 2: Web Presentation for Online Training

```bash
# Same steps 1-3 as above, then:

# 4. Export to reveal.js with custom theme
python export_presentation.py slides_onboarding.json \
  --format revealjs \
  --theme sky \
  --no-embed-images  # Faster loading, requires internet

# Output: onboarding_revealjs.html (open in browser!)
```

### Example 3: Export to All Formats

```bash
# Export to both PPTX and reveal.js
python export_presentation.py slides_onboarding.json --format all

# Creates:
#   - onboarding.pptx
#   - onboarding_revealjs.html
```

---

## 🔧 Advanced Usage

### Custom Output Names

```bash
# Specify custom output filename
python export_presentation.py slides_training.json \
  --format pptx \
  --output "Q4_Sales_Training.pptx"
```

### Faster reveal.js (No Image Embedding)

```bash
# Don't embed images (faster, but needs internet)
python export_presentation.py slides_training.json \
  --format revealjs \
  --no-embed-images
```

### Debug Mode

```bash
# See detailed logs
python export_presentation.py slides_training.json \
  --format pptx \
  --log-level DEBUG
```

---

## 📦 Integration with Existing Workflow

### Update magicSlide.sh

The classic workflow still works, but now you can export to multiple formats:

```bash
# Step 1-4: Generate JSON and markdown
./magicSlide.sh guides/training.md --stop-after=4

# Step 5a: Export to PowerPoint
python export_presentation.py slides_training.json --format pptx

# Step 5b: Or export to reveal.js
python export_presentation.py slides_training.json --format revealjs

# Step 5c: Or keep using Google Slides
python upload_and_fix_images.py slides_training.md
```

---

## 🎨 Customization

### PowerPoint Themes

Currently uses a modern blue theme. To customize colors, edit:

```python
# makeslides/exporters/pptx_exporter.py

PRIMARY_COLOR = RGBColor(0, 120, 212)  # Blue
SECONDARY_COLOR = RGBColor(51, 51, 51)  # Dark gray
ACCENT_COLOR = RGBColor(255, 185, 0)   # Orange
```

### reveal.js Themes

Choose from 10 built-in themes or create custom CSS:

```bash
# Use different theme
python export_presentation.py slides.json \
  --format revealjs \
  --theme solarized
```

---

## 🐛 Troubleshooting

### "No module named 'pptx'"

```bash
pip install python-pptx
```

### "Failed to embed image"

For reveal.js, images need to be accessible. Use Imgur:

```bash
# Upload images to Imgur first
python -m makeslides.images.imgur_uploader images/ --directory

# Update JSON with Imgur URLs
# Then export
```

### PowerPoint won't open

Make sure you have PowerPoint or LibreOffice installed. The .pptx file is compatible with:
- Microsoft PowerPoint (Windows, Mac)
- LibreOffice Impress (Free)
- Google Slides (upload the file)
- Apple Keynote (import)

---

## 📚 Next Steps

1. **Try Phase 1 & 2 features** - Export your presentations
2. **Experiment with themes** - Find your favorite style
3. **Share feedback** - What other formats would you like?
4. **Stay tuned for Phase 3** - Web UI with Supabase + Vercel!

---

## 🆚 Format Comparison

| Feature | PPTX | reveal.js | Google Slides |
|---------|------|-----------|---------------|
| **Offline use** | ✅ Full | ✅ View only | ❌ Internet required |
| **Editing** | ✅ Full PowerPoint | ❌ View only | ✅ Online editing |
| **Sharing** | 📧 Email file | 🔗 URL | 🔗 URL |
| **Collaboration** | ❌ No | ❌ No | ✅ Real-time |
| **Animations** | ⭐ PowerPoint | ⭐⭐⭐ Beautiful | ⭐ Basic |
| **File size** | 📦 Medium | 📦 Small | ☁️ Cloud |
| **Setup** | None | None | OAuth required |
| **Cost** | Free | Free | Free |
| **Best for** | Corporate, offline | Web, demos | Collaboration |

Choose the format that best fits your use case!
