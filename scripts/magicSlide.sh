#!/bin/bash
# magicSlide.sh - One-click slide generation from facilitator guides
# Usage: ./magicSlide.sh input.md [options]
#        ./magicSlide.sh directory/ [options]

# Default options
CONFIG="config.yaml"
MERMAID_CONFIG="mermaid-config.json"
LOG_LEVEL="INFO"
TITLE_PREFIX=""
STYLE="github"
USE_FILEIO=1
CLAUDE_MODEL="claude-3-7-sonnet-20250219"
START_STEP=1  # Default start from beginning
STOP_AFTER=5  # Default run all steps
FULL_CSV=1    # Generate full CSV with all fields by default
PRESERVE_DIAGRAMS=0  # Don't keep multiple versions by default (use asset manager instead)
DEBUG_MODE=0  # Display debug info
USE_ASSET_MANAGER=1  # Use asset manager by default

# Define asset management directory
ASSET_DIR="$HOME/.makeslides/assets"

# Functions
print_usage() {
  echo "Usage: $0 <input.md or directory> [options]"
  echo "Options:"
  echo "  --config=FILE         YAML config file (default: config.yaml)"
  echo "  --mermaid-config=FILE Mermaid config file (default: mermaid-config.json)"
  echo "  --no-fileio           Don't use file.io for image uploads"
  echo "  --title-prefix=TEXT   Add prefix to presentation titles"
  echo "  --style=STYLE         Code highlighting style (default: github)"
  echo "  --model=MODEL         Claude model (default: claude-3-7-sonnet-20250219)"
  echo "  --compact-csv         Generate compact CSV (fewer columns)"
  echo "  --no-full-csv         Don't include diagram content in CSV"
  echo "  --preserve-diagrams   Preserve all diagram versions (default: use asset manager)"
  echo "  --no-asset-manager    Don't use asset manager for caching"
  echo "  --asset-dir=DIR       Directory for asset cache (default: ~/.makeslides/assets)"
  echo "  --log-level=LEVEL     Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)"
  echo "  --start-step=NUM      Start from specific step (1-5, default: 1)"
  echo "  --stop-after=NUM      Stop after specific step (1-5, default: 5)"
  echo "  --debug               Run in debug mode (verbose output, validate markdown)"
  echo "  --verify-npm          Check if npm and md2gslides are installed"
  echo "  --help                Show this help message"
}

# Parse arguments
INPUT=""
for arg in "$@"; do
  case $arg in
    --config=*)
      CONFIG="${arg#*=}"
      ;;
    --mermaid-config=*)
      MERMAID_CONFIG="${arg#*=}"
      ;;
    --no-fileio)
      USE_FILEIO=0
      ;;
    --title-prefix=*)
      TITLE_PREFIX="${arg#*=}"
      ;;
    --style=*)
      STYLE="${arg#*=}"
      ;;
    --model=*)
      CLAUDE_MODEL="${arg#*=}"
      ;;
    --compact-csv)
      FULL_CSV=0
      COMPACT_CSV=1
      ;;
    --no-full-csv)
      FULL_CSV=0
      ;;
    --preserve-diagrams)
      PRESERVE_DIAGRAMS=1
      ;;
    --no-asset-manager)
      USE_ASSET_MANAGER=0
      ;;
    --asset-dir=*)
      ASSET_DIR="${arg#*=}"
      ;;
    --log-level=*)
      LOG_LEVEL="${arg#*=}"
      ;;
    --start-step=*)
      START_STEP="${arg#*=}"
      ;;
    --stop-after=*)
      STOP_AFTER="${arg#*=}"
      ;;
    --debug)
      DEBUG_MODE=1
      LOG_LEVEL="DEBUG"
      ;;
    --verify-npm)
      VERIFY_NPM=1
      ;;
    --help)
      print_usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $arg"
      print_usage
      exit 1
      ;;
    *)
      if [ -z "$INPUT" ]; then
        INPUT="$arg"
      else
        echo "Multiple input files specified. Use only one."
        print_usage
        exit 1
      fi
      ;;
  esac
done

# Check for required input
if [ -z "$INPUT" ]; then
  echo "Error: No input file or directory specified."
  print_usage
  exit 1
fi

# Check for asset manager
check_asset_manager() {
  if [ $USE_ASSET_MANAGER -eq 1 ]; then
    if [ ! -f "asset_manager.py" ]; then
      echo "⚠️  Warning: asset_manager.py not found in the current directory."
      echo "   Asset manager will not be available for caching."
      USE_ASSET_MANAGER=0
    fi
  fi
}

# Verify md2gslides installation early
verify_md2gslides() {
  echo "🔍 Checking md2gslides installation..."
  if ! command -v npm &> /dev/null; then
    echo "❌ npm could not be found. Please install Node.js first."
    echo "   Visit https://nodejs.org/ for installation instructions."
    return 1
  fi
  
  echo "✅ npm is installed: $(npm --version)"
  
  if ! command -v md2gslides &> /dev/null; then
    echo "❌ md2gslides could not be found. Installing it now..."
    npm install -g md2gslides
    
    if [ $? -ne 0 ]; then
      echo "❌ Failed to install md2gslides. Please try manually:"
      echo "   npm install -g md2gslides"
      return 1
    fi
  fi
  
  echo "✅ md2gslides is installed"
  
  # Check for client_id.json
  MD2G_DIR="$HOME/.md2googleslides"
  if [ ! -f "$MD2G_DIR/client_id.json" ]; then
    echo "⚠️  Warning: client_id.json not found at $MD2G_DIR/client_id.json"
    echo "   You may need to set up Google API credentials."
    echo "   See: https://github.com/googleworkspace/md2googleslides#installation-and-usage"
    
    # Create directory if it doesn't exist
    mkdir -p "$MD2G_DIR"
    
    echo "   Please follow these steps to set up Google API credentials:"
    echo "   1. Go to https://console.developers.google.com"
    echo "   2. Create a new project or select an existing one"
    echo "   3. Enable the Google Slides API in the API Library"
    echo "   4. Go to Credentials page and click '+ Create credentials'"
    echo "   5. Select 'OAuth client ID' and 'Desktop Application'"
    echo "   6. Download the JSON file and save it as 'client_id.json' in $MD2G_DIR"
    echo ""
    echo "   Do you want to continue without the credentials? (y/n)"
    read -r continue_without_creds
    
    if [[ $continue_without_creds != "y" && $continue_without_creds != "Y" ]]; then
      echo "Exiting. Please set up credentials and try again."
      return 1
    fi
  else
    echo "✅ Google API credentials found at $MD2G_DIR/client_id.json"
  fi
  
  return 0
}

# Ensure the asset directory exists
mkdir -p "$ASSET_DIR"

# Check for asset manager
check_asset_manager

# Check for md2gslides if requested or if starting from step 5
if [ ${VERIFY_NPM:-0} -eq 1 ] || [ $START_STEP -eq 5 ]; then
  verify_md2gslides || exit 1
fi

# Determine input type
if [ -d "$INPUT" ]; then
  # Directory mode
  echo "🔍 Processing directory: $INPUT"
  WORKING_DIR="$INPUT"
  DIR_MODE=1
else
  # Single file mode
  echo "🔍 Processing file: $INPUT"
  WORKING_DIR="$(dirname "$INPUT")"
  BASENAME="$(basename "$INPUT" .md)"
  BASENAME="${BASENAME%.txt}"  # Also strip .txt if present
  DIR_MODE=0
fi

# Create/verify necessary directories
IMAGES_DIR="$WORKING_DIR/images"
mkdir -p "$IMAGES_DIR"

# Function to check if step should be executed
should_run_step() {
  local step=$1
  if [ $step -ge $START_STEP ] && [ $step -le $STOP_AFTER ]; then
    return 0  # True in bash
  else
    return 1  # False in bash
  fi
}

# Create a progress file to track completed steps
PROGRESS_FILE="$WORKING_DIR/.magicslide_progress"
if [ "$START_STEP" -eq 1 ]; then
  # Starting fresh, remove any existing progress file
  rm -f "$PROGRESS_FILE"
fi

# Create a function for each step that saves progress
run_step() {
  local step_num=$1
  local step_name=$2
  local step_cmd=$3
  
  if should_run_step $step_num; then
    echo "Step $step_num/5: $step_name"
    
    # Run the command
    if eval "$step_cmd"; then
      # Save progress
      echo "$step_num completed" >> "$PROGRESS_FILE"
      return 0
    else
      local exit_code=$?
      echo "❌ Step $step_num failed with exit code $exit_code"
      echo "To resume from this step, run with --start-step=$step_num"
      return $exit_code
    fi
  else
    echo "Skipping Step $step_num/5: $step_name (already completed)"
  fi
}

# Step 1: JSON Generation
if [ $DIR_MODE -eq 1 ]; then
  JSON_STEP="python guide_to_json.py \"$INPUT\" --config=\"$CONFIG\" --model=\"$CLAUDE_MODEL\" --log-level=\"$LOG_LEVEL\""
else
  JSON_FILE="$WORKING_DIR/slides_$BASENAME.json"
  JSON_STEP="python guide_to_json.py \"$INPUT\" --config=\"$CONFIG\" --out=\"$JSON_FILE\" --model=\"$CLAUDE_MODEL\" --log-level=\"$LOG_LEVEL\""
fi
run_step 1 "🧠 Converting to JSON with Claude..." "$JSON_STEP" || exit $?

# Step 2: Diagram Generation
PRESERVE_ARG=""
if [ $PRESERVE_DIAGRAMS -eq 1 ]; then
  PRESERVE_ARG="--preserve-all"
fi

ASSET_MANAGER_ARG=""
if [ $USE_ASSET_MANAGER -eq 1 ]; then
  ASSET_MANAGER_ARG="--use-asset-manager --assets-dir=\"$ASSET_DIR\""
fi

if [ $DIR_MODE -eq 1 ]; then
  DIAGRAM_STEP="python diagrams_to_images.py \"$INPUT\" --mermaid-config=\"$MERMAID_CONFIG\" --output-dir=\"$IMAGES_DIR\" --log-level=\"$LOG_LEVEL\" --model=\"$CLAUDE_MODEL\" $PRESERVE_ARG $ASSET_MANAGER_ARG"
else
  DIAGRAM_STEP="python diagrams_to_images.py \"$JSON_FILE\" --mermaid-config=\"$MERMAID_CONFIG\" --output-dir=\"$IMAGES_DIR\" --log-level=\"$LOG_LEVEL\" --model=\"$CLAUDE_MODEL\" $PRESERVE_ARG $ASSET_MANAGER_ARG"
fi
run_step 2 "📊 Rendering diagrams..." "$DIAGRAM_STEP" || exit $?

# Step 3: CSV Generation
CSV_ARGS=""
if [ $FULL_CSV -eq 1 ]; then
  CSV_ARGS="--full"
elif [ ${COMPACT_CSV:-0} -eq 1 ]; then
  CSV_ARGS="--compact"
fi

if [ $DIR_MODE -eq 1 ]; then
  CSV_STEP="python json_to_csv.py \"$INPUT\" --log-level=\"$LOG_LEVEL\" $CSV_ARGS"
else
  CSV_STEP="python json_to_csv.py \"$JSON_FILE\" --log-level=\"$LOG_LEVEL\" $CSV_ARGS"
fi
run_step 3 "📊 Generating CSV overview..." "$CSV_STEP" || exit $?

# Step 4: Markdown Generation
DEBUG_ARGS=""
if [ $DEBUG_MODE -eq 1 ]; then
  DEBUG_ARGS="--debug"
fi

if [ $DIR_MODE -eq 1 ]; then
  MD_STEP="python json_to_markdown.py \"$INPUT\" --prefer-svg --log-level=\"$LOG_LEVEL\" $DEBUG_ARGS"
else
  MD_STEP="python json_to_markdown.py \"$JSON_FILE\" --prefer-svg --log-level=\"$LOG_LEVEL\" $DEBUG_ARGS"
fi
run_step 4 "📝 Converting to markdown..." "$MD_STEP" || exit $?

# Find markdown files (fixed to use correct naming with "slides_" prefix)
if [ $DIR_MODE -eq 1 ]; then
  # Find all markdown files generated
  MD_FILES=($WORKING_DIR/slides_*.md)
  if [ ${#MD_FILES[@]} -eq 0 ]; then
    echo "❌ No markdown files found in $WORKING_DIR"
    # Try finding any markdown files as fallback
    MD_FILES=($WORKING_DIR/*.md)
    if [ ${#MD_FILES[@]} -eq 0 ]; then
      echo "❌ No markdown files found at all. Cannot proceed."
      exit 1
    fi
    echo "⚠️ Using fallback markdown files without 'slides_' prefix"
  fi
else
  # Use the correct markdown file name with "slides_" prefix
  MD_FILE="$WORKING_DIR/slides_$BASENAME.md"
  
  # Double-check that the file exists
  if [ ! -f "$MD_FILE" ]; then
    echo "❌ Expected markdown file not found: $MD_FILE"
    echo "Checking for alternative files..."
    
    # Try without the "slides_" prefix as a fallback
    ALT_FILE="$WORKING_DIR/$BASENAME.md"
    if [ -f "$ALT_FILE" ]; then
      echo "✅ Found alternative markdown file: $ALT_FILE"
      MD_FILE="$ALT_FILE"
    else
      # List all markdown files in the directory
      echo "Available markdown files:"
      find "$WORKING_DIR" -name "*.md" -type f | while read -r file; do
        echo "  - $(basename "$file")"
      done
      
      echo "Please select which file to use or fix the naming in your scripts."
      exit 1
    fi
  fi
fi

# Step 5: Google Slides Generation
FILEIO_ARG=""
if [ $USE_FILEIO -eq 1 ]; then
  FILEIO_ARG="--use-fileio"
fi

DEBUG_ARG=""
if [ $DEBUG_MODE -eq 1 ]; then
  DEBUG_ARG="--debug"
fi

VERIFY_ARG=""
if [ ${VERIFY_NPM:-0} -eq 1 ]; then
  VERIFY_ARG="--verify-npm"
fi

if [ $DIR_MODE -eq 1 ]; then
  # Process all markdown files
  for md_file in "${MD_FILES[@]}"; do
    echo "Processing markdown file: $md_file"
    md_basename=$(basename "$md_file" .md)
    output_file="$WORKING_DIR/${md_basename}-presentation.txt"
    
    SLIDES_CMD="python build_with_md2gslides.py \"$md_file\" --title-prefix=\"$TITLE_PREFIX\" --style=\"$STYLE\" $FILEIO_ARG --log-level=\"$LOG_LEVEL\" --output-file=\"$output_file\" $DEBUG_ARG $VERIFY_ARG --fix-format"
    echo "Running: $SLIDES_CMD"
    eval "$SLIDES_CMD" || echo "⚠️ Failed to create slides for $md_file"
  done
  # Mark step as complete even if some files failed
  echo "5 completed" >> "$PROGRESS_FILE"
else
  # Process single markdown file
  output_file="$WORKING_DIR/${BASENAME}-presentation.txt"
  SLIDES_STEP="python build_with_md2gslides.py \"$MD_FILE\" --title-prefix=\"$TITLE_PREFIX\" --style=\"$STYLE\" $FILEIO_ARG --log-level=\"$LOG_LEVEL\" --output-file=\"$output_file\" $DEBUG_ARG $VERIFY_ARG --fix-format"

  run_step 5 "🎯 Generating Google Slides..." "$SLIDES_STEP" || {
    echo "❌ Failed to create Google Slides for $MD_FILE"
    echo "Here's the first 20 lines of the markdown file to help diagnose:"
    head -n 20 "$MD_FILE"
    exit 1
  }
fi

echo "✅ All done! Your slides are ready."
echo "📋 Presentation links saved to the output text file."
echo "📊 CSV overview files have been generated for quick reference."

# Print statistics if available
if [ -f "${JSON_FILE:-}" ]; then
  echo ""
  echo "📊 Slide statistics:"
  
  # Count total slides
  TOTAL_SLIDES=$(grep -c "\"slide_number\":" "$JSON_FILE" || echo "0")
  echo "Total slides: $TOTAL_SLIDES"
  
  # Count diagrams
  DIAGRAMS=$(grep -c "\"diagram_type\":" "$JSON_FILE" | grep -v "\"diagram_type\": null" || echo "0")
  echo "Diagrams: $DIAGRAMS"
  
  # Count images
  IMAGES=$(grep -c "\"image_url\":" "$JSON_FILE" | grep -v "\"image_url\": null" || echo "0")
  echo "Images: $IMAGES"
  
  # Count different layouts
  echo ""
  echo "Layout variety:"
  grep -o "\"layout\": \"[^\"]*\"" "$JSON_FILE" | sort | uniq -c
fi

echo ""
echo "If you still have issues with Google Slides generation, try:"
echo "  1. Run with --verify-npm to check Node.js installation"
echo "  2. Make sure md2gslides is installed: npm install -g md2gslides"
echo "  3. Run with --debug to see detailed output"
echo "  4. Check if your Google API credentials are set up correctly"