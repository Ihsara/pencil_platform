# src/constants.py

from dataclasses import dataclass
from pathlib import Path

# --- Project-wide directory structure ---
PROJECT_ROOT = Path(__file__).parent.parent.parent

@dataclass(frozen=True)
class Dirs:
    """Dataclass to hold all major directory paths."""
    root: Path = PROJECT_ROOT
    config: Path = PROJECT_ROOT / "config"
    templates: Path = PROJECT_ROOT / "template" / "generic"
    runs: Path = PROJECT_ROOT / "runs"
    src: Path = PROJECT_ROOT / "src"
    plan_subdir: str = "plan"
    in_subdir: str = "in"

@dataclass(frozen=True)
class Files:
    """Dataclass for standard filenames."""
    plan: str = "sweep.yaml"
    makefile: str = "Makefile_local.yaml"
    cparam: str = "cparam_local.yaml"
    manifest: str = "run_manifest.txt"
    submit_script: str = "submit_suite.sh"

# Instantiate for easy import
DIRS = Dirs()
FILES = Files()
