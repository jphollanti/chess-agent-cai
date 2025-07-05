#!/bin/bash

# === STOCKFISH SETUP ===
URL="https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-macos-m1-apple-silicon.tar"
TAR_FILE="stockfish-macos-m1.tar"
DEST_DIR="./engine/stockfish"

echo "Downloading Stockfish (Apple Silicon)..."
curl -L -o "$TAR_FILE" "$URL"

# Create destination dir and extract tarball directly into it
mkdir -p "$DEST_DIR"
tar -xvf "$TAR_FILE" --strip-components=1 -C "$DEST_DIR"

# Make sure the binary is executable
chmod +x "$DEST_DIR/stockfish"

# Clean up
rm "$TAR_FILE"

echo "Stockfish binary is ready at: $DEST_DIR/stockfish"



# === GM2001.BIN SETUP ===
BOOK_URL="https://raw.githubusercontent.com/michaeldv/donna_opening_books/master/gm2001.bin"
BOOK_DIR="./book"
BOOK_FILE="gm2001.bin"
BOOK_PATH="$BOOK_DIR/$BOOK_FILE"

# Ensure clean directory
rm -rf "$BOOK_DIR"
mkdir -p "$BOOK_DIR"

echo "Downloading gm2001.bin opening book..."
curl -L -o "$BOOK_PATH" "$BOOK_URL"



# === ECO OPENINGS SETUP ===
ECO_DIR="./eco_openings"
ECO_FILES=("ecoA.json" "ecoB.json" "ecoC.json" "ecoD.json" "ecoE.json")
BASE_URL="https://raw.githubusercontent.com/hayatbiralem/eco.json/master"

# Optional: include interpolated ECO if your code uses it
OPTIONAL_FILE="eco_interpolated.json"
OPTIONAL_URL="https://raw.githubusercontent.com/hayatbiralem/eco.json/master/$OPTIONAL_FILE"

# Clean and create directory
rm -rf "$ECO_DIR"
mkdir -p "$ECO_DIR"

echo "Downloading ECO opening files..."

for file in "${ECO_FILES[@]}"; do
    curl -s -o "$ECO_DIR/$file" "$BASE_URL/$file"
    echo "Downloaded: $file"
done

# Download optional interpolated file
echo "Downloading (optional) eco_interpolated.json..."
curl -s -o "$ECO_DIR/$OPTIONAL_FILE" "$OPTIONAL_URL"
echo "Downloaded: $OPTIONAL_FILE"

echo "✅ ECO opening files saved to: $ECO_DIR"