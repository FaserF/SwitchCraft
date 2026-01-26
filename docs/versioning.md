# SwitchCraft Versioning System

SwitchCraft follows a strict versioning schema to ensure compatibility, easy identification of release types, and proper upgrade paths. This document describes how version numbers are generated, how CI handles them, and how they map to different artifacts.

## Version Number Logic

### Base Format
The core version number follows a calendar-based schema:

```
Year.Month.Release
```

*   **Year**: The current year (e.g., `2026`).
*   **Month**: The current month (e.g., `1` for January).
*   **Release**: An incrementing number for releases within that month (e.g., `5`).

Example: `2026.1.5`

### Release Types (Suffixes)
Depending on the build type (Stable, Beta, Development), suffixes are appended to the base version:

| Release Type | Suffix Example | Full Version Example | Description |
| :--- | :--- | :--- | :--- |
| **Stable** | *(None)* | `2026.1.5` | Production-ready official release. |
| **Beta** | `b{N}` | `2026.1.5b1` | Public test build. Stable enough for testing. |
| **Development** | `.dev0+{hash}` | `2026.1.5.dev0+3c4f9a` | CI/Nightly build. Contains latest commit hash. |

---

## Windows Installer Versioning

Windows executables and installers (`.exe`, `.msi`) require a strict 4-part numeric version format (`A.B.C.D`) in their file resources (`VS_VERSION_INFO`).

SwitchCraft maps the semantic version to this 4-part numeric format as follows:

```
Year.Month.Release.BuildNumber
```

*   **Year.Month.Release**: Taken directly from the base version.
*   **BuildNumber**: Derived from the **GitHub Actions Run Number** (CI) or a local counter.

### Why this matters?
Windows uses this 4-part version to decide if an installer is an "Upgrade".
*   `2026.1.5.105` > `2026.1.5.100` -> Windows considers this a new version.
*   Stable releases usually have `0` as the build number base, while Dev builds use the Run Number to ensure every CI build is "newer" than the previous one for testing, but "older" than the next Stable release if semver rules apply (though in Windows, `.100` is > `.0`, so Dev builds might appear "newer" than the *same* stable version. We handle this by bumping the `Release` number for Stable).

### Local Builds
When building locally (using `scripts/build_release.ps1`), you can specify a custom build number to test upgrades:

```powershell
.\scripts\build_release.ps1 -Modern -BuildNumber 999
```

This generates `2026.1.5.999`.

---

## CI/CD Workflow

The release process is automated via GitHub Actions (`.github/workflows/release.yml`).

1.  **Trigger**: Access via "Run workflow" button.
2.  **Input**: Select type (`stable`, `beta`, `dev`).
3.  **Generation**:
    *   The script `.github/scripts/generate_release_version.py` reads `pyproject.toml`.
    *   It calculates the Next Version based on the selected type.
    *   It writes the version back to `pyproject.toml` and generates a `file_version_info.txt`.
4.  **Build**:
    *   PyInstaller builds the app using the generated version info.
    *   Inno Setup compiles the installer, receiving the version string and numeric components.
5.  **Artifacts**:
    *   **Stable**: Uploaded to GitHub Releases.
    *   **Dev/Beta**: Uploaded as Pre-release or Artifacts.

---

## Docker Container Tags

For the SwitchCraft Web/Server backend, Docker tags mimic the release version but replace `+` with `-` (as `+` is invalid in Docker tags).

*   **Stable**: `faserf/switchcraft:2026.1.5`, `faserf/switchcraft:latest`
*   **Beta**: `faserf/switchcraft:2026.1.5b1`
*   **Dev**: `faserf/switchcraft:2026.1.5-dev0-3c4f9a`, `faserf/switchcraft:dev`

This ensures that `latest` always points to the last Stable release, while `dev` points to the latest CI build.
