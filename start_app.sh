#!/bin/bash
# start_app.sh - Launch Beep-Boop with proper environment setup
#
# This script ensures the application starts with correct Python path and environment

echo "🚀 Starting Beep-Boop Application..."
echo "=================================="

# Set PATH to include local Python packages
export PATH=/home/ubuntu/.local/bin:$PATH

# Verify environment
echo "📋 Environment Check:"
echo "  - Python: $(which python3)"
echo "  - ChromaDB: $(python3 -c 'import chromadb; print("✅ Available")' 2>/dev/null || echo "❌ Missing")"
echo "  - Gradio: $(python3 -c 'import gradio; print("✅ Available")' 2>/dev/null || echo "❌ Missing")"

echo ""
echo "🔧 Starting application..."
echo "  - Interface will be available at: http://127.0.0.1:7860"
echo "  - Press Ctrl+C to stop"
echo ""

# Start the application
cd /workspace
python3 app.py