#!/bin/bash
set -e
set -o pipefail

echo "🛠️ Installing development dependencies..."
uv sync --all-extras

echo ""
echo "🪝 Setting up git hooks..."
uv run pre-commit install

echo ""
echo "🌱 Creating .env file..."
rm -f .env
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # On Windows (Git Bash/MSYS2), convert to Windows format
    ROOT_PATH=$(cygpath -m "$(pwd)")
else
    # On Linux/macOS, use the standard absolute path
    ROOT_PATH="$(pwd)"
fi
echo "HOME_ASSISTANT_CONFIG_ROOT=$ROOT_PATH/examples/config" >> .env
echo "APPDAEMON_CONFIG_ROOT=$ROOT_PATH/examples/appdaemon" >> .env

echo ""
echo "🔍 Let's just check everything is working..."
if [[ "$1" != "--skip-checks" ]]; then
  ./run_checks.sh
fi
