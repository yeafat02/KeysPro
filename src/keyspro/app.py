"""Application bootstrap and process-level exception handling."""

from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path
from tkinter import messagebox


def _prepare_direct_execution() -> None:
    """Expose the ``src`` package root when VS Code runs this file directly."""

    if __package__ in {None, ""}:
        source_root = str(Path(__file__).resolve().parents[1])
        if source_root not in sys.path:
            sys.path.insert(0, source_root)


_prepare_direct_execution()


def _enable_high_dpi() -> None:
    """Enable per-monitor DPI awareness when supported by Windows."""

    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            logging.getLogger("keyspro").warning("Could not enable explicit DPI awareness")


def main() -> None:
    """Configure dependencies and start the KeysPro desktop application."""

    from keyspro.config import AppConfig
    from keyspro.logger import configure_logging
    from keyspro.processor import TextConversionService

    config = AppConfig.create()
    logger = configure_logging(config.log_file)
    _enable_high_dpi()

    try:
        from keyspro.ui import KeysProApp

        app = KeysProApp(
            config=config,
            processor=TextConversionService(logger.getChild("processor")),
            logger=logger,
        )
        app.mainloop()
    except Exception as exc:
        logger.exception("KeysPro terminated unexpectedly")
        try:
            messagebox.showerror(
                "KeysPro error",
                "KeysPro could not start. Details were written to the application log.",
            )
        except Exception:
            logger.exception("Could not display the fatal error dialog")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
