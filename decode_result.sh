#!/usr/bin/env bash

JSON_FILE="result.json"
ZIP_FILE="result.zip"

EXTRACT_DIR="result"

# Step 1: Convert JSON Buffer (decimal array) to ZIP
jq -r '.terraformFiles.data[]' "$JSON_FILE" \
  | awk '{printf "%02x", $1}' \
  | xxd -r -p > "$ZIP_FILE"

echo "✅ ZIP file created: $ZIP_FILE"

# Step 2: Create extraction directory
mkdir -p "$EXTRACT_DIR"

# Step 3: Unzip into the directory
unzip -o "$ZIP_FILE" -d "$EXTRACT_DIR"

echo "✅ Files extracted to folder: $EXTRACT_DIR"

# Step 4 (optional): List extracted files
ls -R "$EXTRACT_DIR"
echo "✅ Extraction complete."

# Optional: Clean up the ZIP file if not needed
mv "$ZIP_FILE" $EXTRACT_DIR/