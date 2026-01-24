# libfaketime

**libfaketime is built automatically during container startup.**

Each container (Home Assistant and AppDaemon) builds libfaketime from source during initialization via the `install_libfaketime.sh` script in this directory. This approach:

- ✅ Avoids storing architecture-specific binaries in the repository
- ✅ Ensures compatibility with the container's architecture (x86_64, aarch64, etc.)
- ✅ Uses a single reusable installation script for both containers
- ✅ Pins to an immutable commit SHA to prevent supply-chain attacks
- ✅ Validates SHA256 checksum of the downloaded tarball

## How It Works

The `install_libfaketime.sh` script in this directory performs these steps:

1. Installs build dependencies (curl, make, gcc)
2. Downloads the libfaketime release tarball from commit `6714b98794a9e8a413bf90d2927abf5d888ada99` (`6714b98`, v0.9.11)
3. Verifies the SHA256 checksum to ensure integrity
4. Builds libfaketime from source
5. Installs the compiled library to `/usr/local/lib/faketime/libfaketime.so.1`
6. Configures environment variables for file-based time control

Both entrypoint scripts (`homeassistant/entrypoint.sh` and `appdaemon/entrypoint.sh`) source this installation script during container initialization.

## Security

The installation process includes security measures to prevent supply-chain attacks:

- **Immutable pinning:** Uses a specific commit SHA (`6714b98794a9e8a413bf90d2927abf5d888ada99`) instead of a mutable tag
- **Checksum validation:** Verifies the SHA256 checksum of the downloaded tarball before building
- **Fail-fast:** Any checksum mismatch immediately aborts the installation

## File-Based Time Control

Time is controlled by writing to `/shared_data/.faketime` file in the containers. Format:

- Absolute time: `YYYY-MM-DD HH:MM:SS` (e.g., `2026-01-05 07:30:00`)
- Relative offset: `+Xs` or `-Xs` (e.g., `+60s` for 60 seconds forward)

See `integration_tests/harness/time_machine.py` for the Python API.

## Performance Note

Building libfaketime adds approximately 10-15 seconds to container startup time. This is acceptable for integration tests, which are run less frequently
than unit tests and already have container startup overhead.
