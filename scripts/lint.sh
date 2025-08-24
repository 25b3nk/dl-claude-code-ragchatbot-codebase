#!/bin/bash

# Linting script for the RAG chatbot project
# This script runs code quality checks using flake8

set -e

echo "🔍 Running linting checks with flake8..."
uv run flake8 backend/ main.py --max-line-length=88 --extend-ignore=E203,W503

echo "📋 Checking import formatting..."
uv run isort --check-only backend/ main.py

echo "🖤 Checking code formatting with black..."
uv run black --check backend/ main.py

echo "✅ All quality checks passed!"