#!/bin/bash
set -e
set -o pipefail

echo "✅ Running pre-commit checks..."
uv run pre-commit run --all-files

echo ""
echo "📦 Building package distribution..."
uv run python -m build

echo ""
echo "🔍 Testing package installation..."
# Install the built wheel in a temporary way to test it
WHEEL_FILE=$(find dist -name '*.whl' -printf '%T@ %p\n' | sort -rn | head -n1 | cut -d' ' -f2-)
uv pip install --force-reinstall "$WHEEL_FILE"
uv run python -c "import ha_integration_test_harness; print(f'✅ Successfully imported version {ha_integration_test_harness.__version__}')"

echo ""
echo "🧪 Running example tests..."
HOME_ASSISTANT_CONFIG_ROOT="$(pwd)/examples/config"
export HOME_ASSISTANT_CONFIG_ROOT
APPDAEMON_CONFIG_ROOT="$(pwd)/examples/appdaemon"
export APPDAEMON_CONFIG_ROOT
uv run pytest examples/

echo ""
echo "✅ All checks passed!"
