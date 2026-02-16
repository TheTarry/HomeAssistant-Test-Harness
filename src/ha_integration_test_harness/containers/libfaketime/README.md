# libfaketime

**libfaketime is installed automatically during container startup.**

Each container (Home Assistant and AppDaemon) installs libfaketime from distribution packages during initialization via the `install_libfaketime.sh` script in this directory. This approach:

- ✅ Avoids storing architecture-specific binaries in the repository
- ✅ Ensures compatibility with the container's architecture (x86_64, aarch64, etc.)
- ✅ Uses a single reusable installation script for both containers
- ✅ Fast and reliable (uses pre-compiled packages from official repositories)
- ✅ No build dependencies required

## How It Works

The `install_libfaketime.sh` script in this directory performs these steps:

1. Detects the package manager (apk for Alpine, apt-get for Debian/Ubuntu)
2. Installs libfaketime from official distribution packages
  - Alpine: `apk add libfaketime` (v0.9.12)
  - Debian/Ubuntu: `apt-get install libfaketime` (v0.9.10)
3. Locates the installed library path (architecture-specific)
4. Configures environment variables for file-based time control

Both entrypoint scripts (`homeassistant/entrypoint.sh` and `appdaemon/entrypoint.sh`) source this installation script during container initialization.

## Security

Using distribution packages provides security benefits:

- **Official packages:** Packages are maintained by Alpine and Debian security teams
- **Regular updates:** Security fixes are delivered through standard package updates
- **Verified sources:** Packages are downloaded from official distribution repositories

## File-Based Time Control

Time is controlled by writing to `/shared_data/.faketime` file in the containers. Format:

- Absolute time (prefixed with @): `@YYYY-MM-DD HH:MM:SS` (e.g., `@2026-01-05 07:30:00`)
- Relative offset: `+Xs` or `-Xs` (e.g., `+60s` for 60 seconds forward)

See `src/ha_integration_test_harness/time_machine.py` for the Python API.
