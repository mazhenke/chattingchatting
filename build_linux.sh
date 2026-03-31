#!/bin/bash
set -e

echo "=== Building Anonymous Chat Desktop Client for Linux ==="

# Install build dependencies
pip install pywebview pyinstaller

# Build
pyinstaller --onefile --name anonchat \
    desktop.py

echo ""
echo "Build complete! Binary at: dist/anonchat"
echo "Run with: ./dist/anonchat"
echo "Reconfigure server: ./dist/anonchat --reconfigure"
