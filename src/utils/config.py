"""
Configuration loader for File-Driven Control Plane

Constitutional compliance:
- Section 2 (Source of Truth): Configuration stored in files
- Section 9 (Error Handling): Explicit error handling for config loading
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.control_plane.errors import FileOperationError


def load_config(config_name: str, config_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load YAML configuration file from .specify/config/ directory.

    Args:
        config_name: Name of config file (without .yaml extension)
        config_dir: Optional custom config directory (defaults to .specify/config/)

    Returns:
        Dictionary containing configuration data

    Raises:
        FileOperationError: If config file cannot be read or parsed
    """
    if config_dir is None:
        config_dir = Path(".specify/config")

    config_path = config_dir / f"{config_name}.yaml"

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config if config is not None else {}
    except FileNotFoundError as e:
        raise FileOperationError(
            f"Config file not found: {config_path}"
        ) from e
    except yaml.YAMLError as e:
        raise FileOperationError(
            f"Failed to parse YAML config {config_path}: {e}"
        ) from e
    except OSError as e:
        raise FileOperationError(
            f"Failed to read config {config_path}: {e}"
        ) from e
