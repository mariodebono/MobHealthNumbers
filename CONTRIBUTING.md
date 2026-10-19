# Development

The addon files live at the repository root. WoW loads the three Lua files
listed in `MobHealthNumbers.toc`; no Python installation is needed to use it.
The Python dependency is only for development and offline testing.

## Setup

Create a virtual environment and install the pinned development dependency:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -B tests/test_mob_health.py
```

On Linux or macOS, use `.venv/bin/python` in place of
`.venv\Scripts\python.exe`.

The tests execute the real addon source through Lua 5.1 with mocked WoW APIs.
They cover health learning, damage and healing accounting, persistence, realm
selection, display modes, settings and addon messages. See
[tests/README.md](tests/README.md).

## Build an installable ZIP

```powershell
.venv\Scripts\python.exe tools/package.py
```

The command runs the offline tests, reads the version from the TOC and writes
`dist/MobHealthNumbers-VERSION.zip` with checksums. The archive contains one
`MobHealthNumbers` addon folder, ready to extract into `Interface/AddOns`.
The ZIP checksum is written to a separate `.zip.sha256` file. Development files,
Git metadata and local game data are excluded. The command does not install the
addon or change a WoW client.

For releases, attach this ZIP as the downloadable asset so players get the
expected folder name and layout.

## Release on GitHub

1. Set the release version in `MobHealthNumbers.toc` and update the README download filename.
2. Update `FEATURES.md` with the feature list to display as release notes.
3. Commit and push the changes to the default branch.
4. Open **Actions > Build and release > Run workflow** on GitHub.

The workflow runs only when manually started. It installs the development tools
on GitHub's runner, runs the tests, builds the addon ZIP and creates a release
tagged `vVERSION` at the selected commit. Release notes come from `FEATURES.md`.
The ZIP and its separate checksum are attached as release assets. Players only
need the ZIP; Python is not required to install or use the addon.

Use a new version for each release. An existing release is not overwritten.

## Validate changes in game

Offline tests cannot verify actual client event timing, UI layout or realm
messaging. Before promoting a release, check it in Classic 1.14.2:

1. Install the ZIP in a test client and enable the addon.
2. Observe NPC fights from full health, including healing and multiple attackers.
3. Check numeric target health, mouseover tooltips and saved record counts.
4. Reload and relog; confirm the realm cache and learned records still load.
5. Check settings persistence and optional guild/party sharing with another user.

Only claim compatibility with client versions tested in game. Reports should
include the addon version, client build, reproduction steps and any Lua error,
with personal information removed.
