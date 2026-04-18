"""Centralized path resolution for CDModsElite layout.

All engine modules should use these helpers instead of hardcoding
``game_dir / "CDMods"`` or ``game_dir / "CDModsElite"``.

The folder name changed from ``CDMods`` to ``CDModsElite`` in v4.0.
These helpers transparently fall back to the legacy name so that users
who already have a ``CDMods/vanilla`` backup on disk (from a previous
install) keep working after the upgrade.
"""

from __future__ import annotations
from pathlib import Path


# Canonical name used by this version of the app.
CDMODS_FOLDER = "CDModsElite"
# Legacy name kept for read-only migration fallback.
_CDMODS_LEGACY = "CDMods"


def get_cdmods_dir(game_dir: Path) -> Path:
    """Return the CDModsElite directory for *game_dir*.

    Prefers ``CDModsElite/`` if it already exists; falls back to
    ``CDMods/`` for users who have not yet migrated.  Never creates the
    directory — callers that need it to exist should call ``.mkdir()``.
    """
    elite = game_dir / CDMODS_FOLDER
    if elite.exists():
        return elite
    legacy = game_dir / _CDMODS_LEGACY
    if legacy.exists():
        return legacy
    # Neither exists yet — return the canonical name so callers that
    # *do* mkdir() create the right one.
    return elite


def get_vanilla_dir(game_dir: Path) -> Path:
    """Return the vanilla backup directory for *game_dir*.

    Resolves ``CDModsElite/vanilla`` preferentially, falls back to
    ``CDMods/vanilla`` for pre-v4 installs.  Does NOT create the directory.
    """
    elite_vanilla = game_dir / CDMODS_FOLDER / "vanilla"
    if elite_vanilla.exists():
        return elite_vanilla
    legacy_vanilla = game_dir / _CDMODS_LEGACY / "vanilla"
    if legacy_vanilla.exists():
        return legacy_vanilla
    # Default to elite path even if absent (callers check .exists())
    return elite_vanilla
