"""Application configuration and Windows data-directory management."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Immutable runtime configuration for KeysPro."""

    app_name: str
    version: str
    data_directory: Path
    log_directory: Path
    log_file: Path

    @classmethod
    def create(cls) -> AppConfig:
        """Create configuration using a per-user writable Windows directory."""

        local_app_data = os.environ.get("LOCALAPPDATA")
        base_directory = (
            Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        )
        data_directory = base_directory / "KeysPro"
        log_directory = data_directory / "logs"
        log_directory.mkdir(parents=True, exist_ok=True)
        return cls(
            app_name="KeysPro",
            version="1.0.0",
            data_directory=data_directory,
            log_directory=log_directory,
            log_file=log_directory / "keyspro.log",
        )

