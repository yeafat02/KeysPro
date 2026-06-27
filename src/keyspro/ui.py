"""CustomTkinter user interface for KeysPro."""

from __future__ import annotations

import logging
import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from keyspro.config import AppConfig
from keyspro.models import ConversionOptions, EventKind, ProcessingEvent
from keyspro.processor import ConversionError, TextConversionService


class CreatorInfoDialog(ctk.CTkToplevel):
    """A polished modal card containing the application's creator details."""

    EMAIL = "yeafathossain@gmail.com"

    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        self.title("About KeysPro")
        self.geometry("430x450")
        self.resizable(False, False)
        self.transient(parent)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(self, corner_radius=18)
        card.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="MY",
            width=78,
            height=78,
            corner_radius=39,
            fg_color=("#2563EB", "#3B82F6"),
            text_color="white",
            font=ctk.CTkFont(size=25, weight="bold"),
        ).grid(row=0, column=0, pady=(30, 16))
        ctk.CTkLabel(
            card,
            text="KeysPro",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).grid(row=1, column=0)
        ctk.CTkLabel(
            card,
            text="Innovated by",
            text_color=("gray40", "gray65"),
            font=ctk.CTkFont(size=13),
        ).grid(row=2, column=0, pady=(8, 2))
        ctk.CTkLabel(
            card,
            text="Md. Yeafat",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=3, column=0, pady=(0, 18))

        details = ctk.CTkFrame(card, corner_radius=12, fg_color=("gray92", "gray20"))
        details.grid(row=4, column=0, sticky="ew", padx=28)
        details.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            details,
            text=f"Email\n{self.EMAIL}",
            justify="center",
            font=ctk.CTkFont(size=14),
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(15, 8))
        ctk.CTkLabel(
            details,
            text="Mobile\n01987477615",
            justify="center",
            font=ctk.CTkFont(size=14),
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 15))

        self._copy_button = ctk.CTkButton(
            card,
            text="Copy Email",
            width=130,
            command=self._copy_email,
        )
        self._copy_button.grid(row=5, column=0, pady=(20, 10))
        ctk.CTkLabel(
            card,
            text="Crafted with care for reliable file processing",
            text_color=("gray45", "gray60"),
            font=ctk.CTkFont(size=12),
        ).grid(row=6, column=0, pady=(0, 22))

        self.bind("<Escape>", lambda _event: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(10, self._finish_setup)

    def _finish_setup(self) -> None:
        self.update_idletasks()
        parent = self.master
        x_position = parent.winfo_x() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y_position = parent.winfo_y() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x_position}+{y_position}")
        self.grab_set()
        self.focus_force()

    def _copy_email(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.EMAIL)
        self.update()
        self._copy_button.configure(text="Email Copied")
        self.after(1500, lambda: self._restore_copy_button())

    def _restore_copy_button(self) -> None:
        if self.winfo_exists():
            self._copy_button.configure(text="Copy Email")


class KeysProApp(ctk.CTk, TkinterDnD.DnDWrapper):
    """Main application window with input and processing views."""

    POLL_INTERVAL_MS = 75
    WINDOW_WIDTH = 1060
    WINDOW_HEIGHT = 620

    def __init__(
        self,
        config: AppConfig,
        processor: TextConversionService,
        logger: logging.Logger,
    ) -> None:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        ctk.ThemeManager.theme["CTkFont"].update(
            {"family": "Segoe UI", "size": 15, "weight": "normal"}
        )
        super().__init__()
        detected_window_scaling = self._get_window_scaling()
        ctk.set_window_scaling(1.0 / detected_window_scaling)
        ctk.set_widget_scaling(1.0 / detected_window_scaling)
        TkinterDnD._require(self)

        self._config = config
        self._processor = processor
        self._logger = logger
        self._event_queue: queue.Queue[ProcessingEvent | Exception] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._output_path: Path | None = None
        self._input_active = False
        self._processing_active = False
        self._output_folder_user_selected = False
        self._creator_dialog: CreatorInfoDialog | None = None
        self._appearance_choice = "System"

        self.title(f"{config.app_name} {config.version}")
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.minsize(900, 560)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=0, column=0, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self.bind("<Control-o>", lambda _event: self._choose_file())
        self.bind("<Control-Return>", lambda _event: self._start_processing())
        self.bind("<Control-l>", lambda _event: self._show_input_screen())
        self.bind("<Control-q>", self._show_creator_info)
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._handle_drop)
        self.protocol("WM_DELETE_WINDOW", self._close_application)

        self._show_input_screen()
        self.after(100, self._center_main_window)

    def _center_main_window(self) -> None:
        x_position = max(0, (self.winfo_screenwidth() - self.WINDOW_WIDTH) // 2)
        y_position = max(0, (self.winfo_screenheight() - self.WINDOW_HEIGHT) // 2)
        self.geometry(
            f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x_position}+{y_position}"
        )

    def _show_creator_info(self, _event: Any = None) -> str:
        if self._creator_dialog is not None and self._creator_dialog.winfo_exists():
            self._creator_dialog.focus_force()
            return "break"
        self._creator_dialog = CreatorInfoDialog(self)
        return "break"

    def _clear_content(self) -> None:
        for child in self._content.winfo_children():
            child.destroy()

    def _show_input_screen(self) -> None:
        if self._processing_active:
            return

        self._clear_content()
        self._output_path = None
        self._input_active = True
        self._output_folder_user_selected = False

        wrapper = ctk.CTkFrame(self._content, fg_color="transparent")
        wrapper.grid(row=0, column=0, sticky="nsew", padx=32, pady=24)
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(wrapper, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="KeysPro",
            font=ctk.CTkFont(size=32, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Convert key records safely and quickly",
            text_color=("gray35", "gray70"),
            font=ctk.CTkFont(size=15),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._theme_menu = ctk.CTkOptionMenu(
            header,
            values=["System", "Light", "Dark"],
            width=110,
            command=self._change_appearance_mode,
        )
        self._theme_menu.set(self._appearance_choice)
        self._theme_menu.grid(row=0, column=1, rowspan=2, sticky="e")

        card = ctk.CTkFrame(
            wrapper,
            corner_radius=16,
            border_width=1,
            border_color=("gray78", "gray28"),
        )
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(6, weight=1)

        field_label_font = ctk.CTkFont(size=15, weight="bold")
        ctk.CTkLabel(
            card,
            text="MID (maximum 15 letters or numbers)",
            anchor="w",
            font=field_label_font,
        ).grid(
            row=0, column=0, sticky="ew", padx=(28, 12), pady=(28, 6)
        )
        ctk.CTkLabel(card, text="Index", anchor="w", font=field_label_font).grid(
            row=0, column=1, sticky="ew", padx=(12, 28), pady=(28, 6)
        )
        mid_validation = (self.register(self._validate_mid_keystroke), "%P")
        self._mid_entry = ctk.CTkEntry(
            card,
            height=46,
            placeholder_text="Example: ABC123456",
            validate="key",
            validatecommand=mid_validation,
        )
        self._mid_entry.grid(row=1, column=0, sticky="ew", padx=(28, 12))
        self._index_entry = ctk.CTkEntry(card, height=46, placeholder_text="Example: 1")
        self._index_entry.grid(row=1, column=1, sticky="ew", padx=(12, 28))

        ctk.CTkLabel(
            card, text="Input text file", anchor="w", font=field_label_font
        ).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=28, pady=(22, 6)
        )
        file_row = ctk.CTkFrame(card, fg_color="transparent")
        file_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=28)
        file_row.grid_columnconfigure(0, weight=1)
        self._file_entry = ctk.CTkEntry(
            file_row,
            height=46,
            placeholder_text="Select or drop a .txt file",
        )
        self._file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(
            file_row,
            text="Browse",
            width=110,
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._choose_file,
        ).grid(row=0, column=1)

        ctk.CTkLabel(card, text="Output folder", anchor="w", font=field_label_font).grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=28, pady=(18, 6)
        )
        output_row = ctk.CTkFrame(card, fg_color="transparent")
        output_row.grid(row=5, column=0, columnspan=2, sticky="ew", padx=28)
        output_row.grid_columnconfigure(0, weight=1)
        self._output_folder_entry = ctk.CTkEntry(
            output_row,
            height=46,
            placeholder_text="Select where the converted file will be saved",
        )
        self._output_folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(
            output_row,
            text="Browse",
            width=110,
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._choose_output_folder,
        ).grid(row=0, column=1)

        drop_area = ctk.CTkLabel(
            card,
            text=(
                "Drop a text file anywhere in this window\n\n"
                "Ctrl+O to browse  •  Ctrl+Enter to process"
            ),
            corner_radius=12,
            fg_color=("gray88", "gray22"),
            text_color=("gray35", "gray70"),
            font=ctk.CTkFont(size=15),
        )
        drop_area.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=28, pady=22)

        self._process_button = ctk.CTkButton(
            card,
            text="Process File",
            height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._start_processing,
        )
        self._process_button.grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=28, pady=(0, 28)
        )
        self.after(100, self._mid_entry.focus_set)

    def _change_appearance_mode(self, selected_mode: str) -> None:
        self._appearance_choice = selected_mode
        ctk.set_appearance_mode(selected_mode)

    def _choose_file(self) -> None:
        if not self._input_active:
            return
        file_name = filedialog.askopenfilename(
            parent=self,
            title="Select input text file",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if file_name:
            self._set_file_path(Path(file_name))

    def _handle_drop(self, event: Any) -> str:
        if not self._input_active:
            return "break"
        try:
            dropped_items = self.tk.splitlist(event.data)
            if dropped_items:
                self._set_file_path(Path(dropped_items[0]))
        except (ValueError, TypeError, AttributeError) as exc:
            self._logger.warning("Could not parse dropped file: %s", exc)
            messagebox.showerror(
                "Invalid drop",
                "Could not read the dropped file path.",
                parent=self,
            )
        return "break"

    def _choose_output_folder(self) -> None:
        if not self._input_active:
            return
        current_value = self._output_folder_entry.get().strip()
        initial_directory = (
            current_value if current_value and Path(current_value).is_dir() else None
        )
        folder_name = filedialog.askdirectory(
            parent=self,
            title="Select output folder",
            initialdir=initial_directory,
            mustexist=True,
        )
        if folder_name:
            self._output_folder_user_selected = True
            self._set_entry_value(self._output_folder_entry, folder_name)

    def _set_file_path(self, path: Path) -> None:
        self._set_entry_value(self._file_entry, str(path))
        if not self._output_folder_user_selected:
            self._set_entry_value(self._output_folder_entry, str(path.parent))

    @staticmethod
    def _set_entry_value(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    @staticmethod
    def _validate_mid_keystroke(proposed_value: str) -> bool:
        return not proposed_value or (
            proposed_value.isascii()
            and proposed_value.isalnum()
            and len(proposed_value) <= 15
        )

    def _validate_input(self) -> tuple[Path, Path, ConversionOptions] | None:
        input_path = Path(self._file_entry.get().strip())
        output_directory_value = self._output_folder_entry.get().strip()
        output_directory = Path(output_directory_value)
        options = ConversionOptions(
            mid=self._mid_entry.get().strip(),
            index=self._index_entry.get().strip(),
        )
        try:
            self._processor.validate_options(options)
            if not input_path.is_file():
                raise ValueError("Please select an existing input file.")
            if input_path.suffix.lower() != ".txt":
                raise ValueError("Please select a .txt input file.")
            if not output_directory_value:
                raise ValueError("Please select an output folder.")
            if not output_directory.is_dir():
                raise ValueError("Please select an existing output folder.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Check input", str(exc), parent=self)
            return None
        return input_path, output_directory, options

    def _start_processing(self) -> None:
        if not self._input_active or self._processing_active:
            return
        validated = self._validate_input()
        if validated is None:
            return

        input_path, output_directory, options = validated
        output_path = self._processor.default_output_path(input_path, output_directory)
        self._show_processing_screen()
        self._worker = threading.Thread(
            target=self._run_conversion,
            args=(input_path, output_path, options),
            name="keyspro-converter",
            daemon=True,
        )
        self._worker.start()
        self.after(self.POLL_INTERVAL_MS, self._poll_events)

    def _show_processing_screen(self) -> None:
        self._input_active = False
        self._processing_active = True
        self._clear_content()
        wrapper = ctk.CTkFrame(self._content, fg_color="transparent")
        wrapper.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            wrapper,
            text="Processing file",
            font=ctk.CTkFont(size=30, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        self._status_label = ctk.CTkLabel(
            wrapper,
            text="Preparing...",
            anchor="w",
            text_color=("gray35", "gray70"),
            font=ctk.CTkFont(size=15),
        )
        self._status_label.grid(row=1, column=0, sticky="ew", pady=(5, 12))
        self._progress_bar = ctk.CTkProgressBar(wrapper, height=12)
        self._progress_bar.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        self._progress_bar.set(0)

        panels = ctk.CTkFrame(wrapper, fg_color="transparent")
        panels.grid(row=3, column=0, sticky="nsew")
        panels.grid_columnconfigure(0, weight=1)
        panels.grid_columnconfigure(1, weight=1)
        panels.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            panels,
            text="Activity",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6)
        )
        ctk.CTkLabel(
            panels,
            text="Converted output",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 6))
        self._activity_text = ctk.CTkTextbox(
            panels,
            wrap="word",
            state="disabled",
            font=ctk.CTkFont(size=14),
            corner_radius=10,
        )
        self._activity_text.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self._output_text = ctk.CTkTextbox(
            panels,
            wrap="none",
            state="disabled",
            font=ctk.CTkFont(family="Consolas", size=14),
            corner_radius=10,
        )
        self._output_text.grid(row=1, column=1, sticky="nsew", padx=(8, 0))

        self._summary_label = ctk.CTkLabel(
            wrapper,
            text="",
            anchor="w",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self._summary_label.grid(row=4, column=0, sticky="ew", pady=(14, 10))
        button_row = ctk.CTkFrame(wrapper, fg_color="transparent")
        button_row.grid(row=5, column=0, sticky="ew")
        button_row.grid_columnconfigure(0, weight=1)
        self._another_button = ctk.CTkButton(
            button_row,
            text="Process Another File",
            width=180,
            height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled",
            command=self._show_input_screen,
        )
        self._another_button.grid(row=0, column=1, padx=(0, 10))
        self._open_button = ctk.CTkButton(
            button_row,
            text="Open Output File",
            width=160,
            height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            state="disabled",
            command=self._open_output_file,
        )
        self._open_button.grid(row=0, column=2)

    def _run_conversion(
        self,
        input_path: Path,
        output_path: Path,
        options: ConversionOptions,
    ) -> None:
        try:
            self._processor.process_file(
                input_path=input_path,
                options=options,
                callback=self._event_queue.put,
                output_path=output_path,
            )
        except Exception as exc:  # Thread boundary: relay all failures to the UI.
            self._logger.exception("File conversion failed")
            self._event_queue.put(exc)

    def _poll_events(self) -> None:
        while True:
            try:
                item = self._event_queue.get_nowait()
            except queue.Empty:
                break

            if isinstance(item, Exception):
                self._handle_processing_error(item)
                return
            self._handle_processing_event(item)

        if self._processing_active:
            self.after(self.POLL_INTERVAL_MS, self._poll_events)

    def _handle_processing_event(self, event: ProcessingEvent) -> None:
        self._status_label.configure(text=event.message)
        self._progress_bar.set(event.progress)
        self._append_text(self._activity_text, event.message)
        if event.output_line:
            self._append_text(self._output_text, event.output_line)

        if event.kind is EventKind.COMPLETE and event.summary is not None:
            summary = event.summary
            self._processing_active = False
            self._output_path = summary.output_path
            self._summary_label.configure(
                text=(
                    f"Converted: {summary.converted_records}   •   "
                    f"Duplicates: {summary.duplicate_records}   •   "
                    f"Invalid: {summary.invalid_records}"
                )
            )
            self._open_button.configure(state="normal")
            self._another_button.configure(state="normal")

    @staticmethod
    def _append_text(textbox: ctk.CTkTextbox, message: str) -> None:
        textbox.configure(state="normal")
        textbox.insert("end", f"{message}\n\n")
        textbox.see("end")
        textbox.configure(state="disabled")

    def _handle_processing_error(self, error: Exception) -> None:
        self._processing_active = False
        friendly_message = (
            str(error)
            if isinstance(error, ConversionError | ValueError)
            else "An unexpected error occurred. Details were written to the application log."
        )
        self._status_label.configure(text="Conversion failed.")
        self._append_text(self._activity_text, f"Error: {friendly_message}")
        self._summary_label.configure(text="No output file was created.")
        self._another_button.configure(state="normal")
        messagebox.showerror("Conversion failed", friendly_message, parent=self)

    def _open_output_file(self) -> None:
        if self._output_path is None or not self._output_path.is_file():
            messagebox.showerror(
                "File unavailable",
                "The output file could not be found.",
                parent=self,
            )
            return
        try:
            os.startfile(self._output_path)  # type: ignore[attr-defined]
        except OSError as exc:
            self._logger.exception("Could not open output file %s", self._output_path)
            messagebox.showerror("Could not open file", str(exc), parent=self)

    def _close_application(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            should_close = messagebox.askyesno(
                "Processing in progress",
                "A file is still being processed. Close KeysPro anyway?",
                parent=self,
            )
            if not should_close:
                return
        self.destroy()
