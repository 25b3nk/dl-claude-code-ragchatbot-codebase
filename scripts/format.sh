#!/bin/bash

# Code formatting script for the RAG chatbot project
# This script formats all Python files using black and isort

set -e

echo "🎨 Formatting Python code with black..."
uv run black backend/ main.py

echo "📦 Sorting imports with isort..."
uv run isort backend/ main.py

echo "✅ Code formatting complete!"