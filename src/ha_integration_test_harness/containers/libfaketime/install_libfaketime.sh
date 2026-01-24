#!/usr/bin/env sh
set -e

# install_libfaketime.sh
# Builds libfaketime from source for the current architecture and installs it.
# This script is called by both homeassistant and appdaemon entrypoint scripts.

# IMPORTANT: Pinned to immutable commit SHA to prevent supply-chain attacks
# See: https://github.com/wolfcw/libfaketime/releases
# Version: v0.9.11
LIBFAKETIME_COMMIT="6714b98794a9e8a413bf90d2927abf5d888ada99"
LIBFAKETIME_VERSION="v0.9.11"
LIBFAKETIME_SHA256="842862ebcfc278d084be8c6e40cd82a8384f1468bed6d1fe17f2ff65575fdbc4"
INSTALL_DIR="/usr/local/lib/faketime"

echo "📅 Installing libfaketime ${LIBFAKETIME_VERSION}..."

# Install build dependencies
echo "📦 Installing build dependencies..."
if command -v apk > /dev/null 2>&1; then
    # Alpine Linux (AppDaemon container)
    apk add --no-cache curl make gcc musl-dev
elif command -v apt-get > /dev/null 2>&1; then
    # Debian/Ubuntu (Home Assistant container)
    apt-get update -qq
    apt-get install -y -qq curl make gcc libc6-dev > /dev/null 2>&1
else
    echo "❌ Unsupported package manager. Cannot install build dependencies."
    exit 1
fi

# Download and verify libfaketime release tarball
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

COMMIT_SHORT=$(echo "$LIBFAKETIME_COMMIT" | cut -c1-7)
echo "🔽 Downloading libfaketime ${LIBFAKETIME_VERSION} (commit: ${COMMIT_SHORT})..."
TARBALL_URL="https://github.com/wolfcw/libfaketime/archive/${LIBFAKETIME_COMMIT}.tar.gz"
curl --connect-timeout 30 --max-time 300 -fsSL -o libfaketime.tar.gz "$TARBALL_URL"

echo "🔐 Verifying checksum..."
# Note: sha256sum -c expects format "checksum  filename" (two spaces before filename)
echo "${LIBFAKETIME_SHA256}  libfaketime.tar.gz" | sha256sum -c - || {
    echo "❌ Checksum verification failed!"
    echo "   Expected: ${LIBFAKETIME_SHA256}"
    ACTUAL_SHA256=$(sha256sum libfaketime.tar.gz 2>/dev/null | awk '{print $1}')
    if [ -n "$ACTUAL_SHA256" ]; then
        echo "   Actual:   ${ACTUAL_SHA256}"
    else
        echo "   Actual:   (unable to compute checksum)"
    fi
    echo "   This indicates a potential supply-chain attack or corrupted download."
    exit 1
}

echo "✅ Checksum verified"
tar -xzf libfaketime.tar.gz
EXTRACTED_DIR="libfaketime-${LIBFAKETIME_COMMIT}"
if [ ! -d "$EXTRACTED_DIR" ]; then
    echo "❌ Expected directory '$EXTRACTED_DIR' not found after extracting libfaketime tarball."
    echo "   This may indicate a change in the archive format or an extraction error."
    exit 1
fi
cd "$EXTRACTED_DIR"

echo "🔨 Building libfaketime..."
make

# Install the library
echo "📥 Installing libfaketime to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
# Ensure we copy the **multithreaded** version of the library - to avoid instability in
# reading/writing the timestamp file from both HA/AppDaemon and test harness threads.
cp src/libfaketimeMT.so.1 "${INSTALL_DIR}/libfaketime.so.1"

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo "✅ libfaketime installed successfully"

# Export environment variables to "activate" libfaketime
export FAKETIME_TIMESTAMP_FILE=/shared_data/.faketime
export FAKETIME_NO_CACHE=1

# Preload libfaketime for all processes spawned from this point onward
export LD_PRELOAD="${INSTALL_DIR}/libfaketime.so.1"

# Initialize the timestamp file with +0 (use real time with no offset).
# The test harness will update this file whenever it manipulates the simulated time.
mkdir -p /shared_data
echo -n "+0" > /shared_data/.faketime.tmp
mv /shared_data/.faketime.tmp /shared_data/.faketime

echo "✅ libfaketime configured (time control via ${FAKETIME_TIMESTAMP_FILE})"
