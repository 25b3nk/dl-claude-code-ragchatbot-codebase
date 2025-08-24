#!/bin/bash

# Complete quality check script for the RAG chatbot project
# This script runs formatting, linting, and tests

set -e

echo "🚀 Starting complete quality check..."

echo "1️⃣ Installing/syncing dependencies..."
uv sync --group dev

echo "2️⃣ Formatting code..."
./scripts/format.sh

echo "3️⃣ Running linting checks..."
./scripts/lint.sh

echo "4️⃣ Running tests..."
cd backend && uv run pytest tests/ -v

echo "🎉 All quality checks and tests passed!"
echo "Your code is ready for commit! 🚀"