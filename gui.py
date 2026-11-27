"""Local desktop interface for Kundali Local."""

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from palmistry import LINES, detect_lines

ROOT = Path(__file__).resolve().parent
CLI_MODULES = {"kundli", "numerology", "palmistry"}
RUNNER = (
    "import importlib, json, sys; "
    "module, args = json.load(sys.stdin); "
    "sys.argv = [module + '.py', *args]; "
    "importlib.import_module(module).main()"
)


def run_cli(module, args):
    if module not in CLI_MODULES:
        raise ValueError("Unknown calculator.")
    result = subprocess.run(
        [sys.executable, "-c", RUNNER], cwd=ROOT,
        input=json.dumps([module, args]), capture_output=True,
        encoding="utf-8", timeout=150,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode and not output:
        raise ValueError("The calculator stopped without a result.")
    return output


class KundaliApp:
    def __init__(self, root):
        self.root = root
        self.results = queue.Queue()
        self.busy = False
        root.title("Kundali Local")
        root.geometry("900x760")
        root.minsize(640, 650)

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Kundali Local", font=("TkDefaultFont", 22, "bold")).pack(anchor="w")
        settings = ttk.Frame(main, padding=(0, 8))
        settings.pack(fill="x")
        self.mode = self.field(settings, 0, "Reading mode", "offline", ("offline", "ollama", "openai"))
        self.model = self.field(settings, 1, "AI model name", "")
        settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text="OpenAI uses OPENAI_API_KEY from your environment.").grid(
            row=2, column=1, sticky="w"
        )

        tabs = ttk.Notebook(main)
        tabs.pack(fill="x", pady=(0, 10))
        chart, numbers, palm = [ttk.Frame(tabs, padding=10) for _ in range(3)]
        for frame, title in zip((chart, numbers, palm), ("Vedic chart", "Numerology", "Palmistry")):
            tabs.add(frame, text=title)
            frame.columnconfigure(1, weight=1)

        self.birth = self.field(chart, 0, "Birth date and time (YYYY-MM-DD HH:MM)", "")
        self.zone = self.field(chart, 1, "Birth time zone (e.g. Asia/Kolkata)", "")
        self.latitude = self.field(chart, 2, "Latitude (decimal degrees)", "")
        self.longitude = self.field(chart, 3, "Longitude (east positive)", "")
        self.as_of = self.field(chart, 4, "Reading date (YYYY-MM-DD)", date.today().isoformat())
        self.topic = self.field(chart, 5, "Reading focus", "overview", ("overview", "career", "relationships"))
        self.fold = self.field(chart, 6, "Repeated clock time", "automatic", ("automatic", "earlier", "later"))
        self.transits = tk.BooleanVar(value=True)
        self.lal = tk.BooleanVar()
        ttk.Checkbutton(chart, text="Show transits and next 31 days of dasha changes", variable=self.transits).grid(
            row=7, column=0, columnspan=2, sticky="w"
        )
        ttk.Checkbutton(chart, text="Show Lal Kitab house placements", variable=self.lal).grid(
            row=8, column=0, columnspan=2, sticky="w"
        )
        ttk.Button(chart, text="Calculate chart", command=self.chart).grid(row=9, column=0, sticky="w")

        self.number_birth = self.field(numbers, 0, "Birth date (YYYY-MM-DD)", "")
        self.year = self.field(numbers, 1, "Personal Year", str(date.today().year))
        ttk.Button(numbers, text="Calculate numbers", command=self.numerology).grid(row=2, column=0, sticky="w")

        self.hand = self.field(palm, 0, "Hand", "right", ("right", "left"))
        self.lines = {
            name: self.field(palm, row, f"{name.title()} line", "unknown", ("unknown", *shapes))
            for row, (name, (_, shapes)) in enumerate(LINES.items(), start=1)
        }
        ttk.Button(palm, text="Choose photo and suggest lines", command=self.photo).grid(
            row=5, column=0, sticky="w"
        )
        ttk.Button(palm, text="Read selected lines", command=self.palm).grid(row=5, column=1, sticky="w")
        ttk.Label(palm, text="Review the suggested line shapes before requesting a reading.").grid(
            row=6, column=0, columnspan=2, sticky="w"
        )

        output_header = ttk.Frame(main)
        output_header.pack(fill="x")
        ttk.Label(output_header, text="Results", font=("TkDefaultFont", 13, "bold")).pack(side="left")
        ttk.Button(output_header, text="Clear", command=lambda: self.show("")).pack(side="right")
        self.output = ScrolledText(main, wrap="word", height=10, padx=10, pady=8)
        self.output.pack(fill="both", expand=True, pady=(4, 0))
        self.output.configure(state="disabled")
        root.after(100, self.poll)

    @staticmethod
    def field(parent, row, label, default, choices=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=2)
        value = tk.StringVar(value=default)
        if choices:
            widget = ttk.Combobox(parent, textvariable=value, values=choices, state="readonly")
        else:
            widget = ttk.Entry(parent, textvariable=value, width=34)
        widget.grid(row=row, column=1, sticky="ew", pady=2)
        return value

    def show(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def submit(self, task, on_success):
        if self.busy:
            return
        self.busy = True
        self.show("Working…")

        def worker():
            try:
                self.results.put((on_success, task()))
            except (ValueError, OSError, subprocess.TimeoutExpired) as error:
                self.results.put((self.show, f"Could not complete the reading: {error}"))

        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            callback, result = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            callback(result)
        self.root.after(100, self.poll)

    def reading_args(self):
        mode = self.mode.get()
        model = self.model.get().strip()
        if mode != "offline" and not model:
            messagebox.showinfo("Choose a model", "Enter the AI model name or choose offline mode.")
            return None
        return ["--reading", mode, "--model", model] if mode != "offline" else ["--reading", mode]

    def chart(self):
        if self.busy:
            return
        reading = self.reading_args()
        if reading is None:
            return
        if self.mode.get() == "openai" and not messagebox.askokcancel(
            "Send chart to OpenAI?",
            "OpenAI will receive derived chart placements, dasha dates, and requested transits.",
        ):
            return
        birth = self.birth.get().strip().replace(" ", "T", 1)
        args = [birth, self.zone.get().strip(), self.latitude.get().strip(),
                self.longitude.get().strip(), "--topic", self.topic.get(), *reading]
        if self.as_of.get().strip():
            args.extend(("--as-of", self.as_of.get().strip()))
        if self.fold.get() != "automatic":
            args.extend(("--fold", "0" if self.fold.get() == "earlier" else "1"))
        if self.transits.get():
            args.extend(("--transits", "--timeline", "31"))
        if self.lal.get():
            args.append("--lal-kitab")
        self.submit(lambda: run_cli("kundli", args), self.show)

    def numerology(self):
        args = [self.number_birth.get().strip(), "--year", self.year.get().strip()]
        self.submit(lambda: run_cli("numerology", args), self.show)

    def photo(self):
        if self.busy:
            return
        mode, model = self.mode.get(), self.model.get().strip()
        if mode == "offline" or not model:
            messagebox.showinfo("Vision model needed", "Choose Ollama or OpenAI and enter a vision model name.")
            return
        path = filedialog.askopenfilename(filetypes=[("Palm photos", "*.jpg *.jpeg *.png")])
        if not path:
            return
        if mode == "openai" and not messagebox.askokcancel(
            "Upload palm photo to OpenAI?",
            "The selected image, including any embedded metadata, will be sent to OpenAI.",
        ):
            return

        def show_suggestions(suggestions):
            for name, field in self.lines.items():
                field.set(suggestions.get(name, "unknown"))
            self.show("Review or edit the suggested line shapes, then select Read selected lines.")

        self.submit(lambda: detect_lines(Path(path), mode, model), show_suggestions)

    def palm(self):
        if self.busy:
            return
        reading = self.reading_args()
        if reading is None:
            return
        selected = [item for name, value in self.lines.items() if value.get() != "unknown"
                    for item in (f"--{name}", value.get())]
        if not selected:
            self.show("Select at least one palm line shape.")
            return
        if self.mode.get() == "openai" and not messagebox.askokcancel(
            "Send palm descriptions to OpenAI?",
            "OpenAI will receive the selected hand and line shapes.",
        ):
            return
        args = ["--hand", self.hand.get(), *selected, *reading]
        self.submit(lambda: run_cli("palmistry", args), self.show)


def main():
    root = tk.Tk()
    KundaliApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
