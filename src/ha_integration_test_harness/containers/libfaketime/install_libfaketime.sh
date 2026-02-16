#!/usr/bin/env sh
set -e

# install_libfaketime.sh
# Installs libfaketime from distribution packages.
# This script is called by both homeassistant and appdaemon entrypoint scripts.

echo "📅 Installing libfaketime from distribution packages..."

# Detect package manager and install libfaketime
if command -v apk > /dev/null 2>&1; then
    echo "📦 Installing libfaketime on Alpine..."
    apk add --no-cache libfaketime
    # Use multi-threaded variant (MT) - essential for Home Assistant's multi-threaded environment
    LIBFAKETIME_PATH="/usr/lib/faketime/libfaketimeMT.so.1"
elif command -v apt-get > /dev/null 2>&1; then
    echo "📦 Installing libfaketime on Debian/Ubuntu..."
    apt-get update -qq
    apt-get install -y -qq libfaketime > /dev/null 2>&1
    # Debian installs to /usr/lib/<arch>/faketime/libfaketimeMT.so.1
    # Find the actual path (could be x86_64-linux-gnu, aarch64-linux-gnu, etc.)
    # Use multi-threaded variant (MT) - essential for Home Assistant's multi-threaded environment
    LIBFAKETIME_PATH=$(find /usr/lib -name "libfaketimeMT.so.1" 2>/dev/null | head -n 1)
    if [ -z "$LIBFAKETIME_PATH" ]; then
        echo "❌ libfaketime library not found after installation"
        exit 1
    fi
else
    echo "❌ Unsupported package manager. Cannot install libfaketime."
    exit 1
fi

echo "✅ libfaketime installed successfully"
echo "   Library path: ${LIBFAKETIME_PATH}"

# Export environment variables to "activate" libfaketime
export FAKETIME_TIMESTAMP_FILE=/shared_data/.faketime
export FAKETIME_NO_CACHE=1

# Preload libfaketime for all processes spawned from this point onward
export LD_PRELOAD="${LIBFAKETIME_PATH}"

# Initialize the timestamp file with +0 (use real time with no offset).
# The test harness will update this file whenever it manipulates the simulated time.
mkdir -p /shared_data
printf "+0" > /shared_data/.faketime.tmp
mv /shared_data/.faketime.tmp /shared_data/.faketime

echo "✅ libfaketime configured (time control via ${FAKETIME_TIMESTAMP_FILE})"
