#!/bin/bash
set -e
set -o pipefail

echo "🛠️ Installing development dependencies..."
uv sync --all-extras

echo ""
echo "🪝 Setting up git hooks..."
uv run pre-commit install

echo ""
echo "🔍 Let's just check everything is working..."
if [[ "$1" != "--skip-checks" ]]; then
  ./run_checks.sh
fi
