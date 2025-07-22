#!/bin/bash

# 🧠 Agentic Companion Setup Script
# This script helps you set up and run your agentic companion project

echo "🧠 Setting up Agentic Companion..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env_template.txt .env
    echo "⚠️  Please edit .env file and add your API keys!"
    echo "   - OPENAI_API_KEY (required)"
    echo "   - ANTHROPIC_API_KEY (optional)"
    echo "   - ELEVENLABS_API_KEY (optional)"
else
    echo "✅ .env file already exists"
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p chroma_db

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not detected!"
    echo "   Please activate your virtual environment:"
    echo "   source .venv/bin/activate"
else
    echo "✅ Virtual environment is active"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Open agentic_companion_dev.ipynb in Jupyter or VS Code"
echo "3. Run through the notebook cells"
echo "4. Launch the Gradio interface"
echo ""
echo "Happy building! 🚀" 