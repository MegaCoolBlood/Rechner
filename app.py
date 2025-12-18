import ast
import operator
import ctypes
from ctypes import wintypes
import math
import sys
import tkinter as tk
from tkinter import messagebox, ttk


class SafeEvaluator:
    """Evaluates math expressions using AST to avoid executing arbitrary code."""

    _binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
    }
    _unary_ops = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    @classmethod
    def evaluate(cls, expression: str) -> float:
        expression = expression.replace(" ", "").replace(",", ".").strip()
        if not expression:
            return 0.0
        try:
            tree = ast.parse(expression, mode="eval")
            return float(cls._eval_node(tree.body))
        except Exception as exc:  # noqa: BLE001 - show a friendly error via UI
            raise ValueError("Ungültiger Ausdruck") from exc

    @classmethod
    def _eval_node(cls, node):
        if isinstance(node, ast.BinOp) and type(node.op) in cls._binary_ops:
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            return cls._binary_ops[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in cls._unary_ops:
            return cls._unary_ops[type(node.op)](cls._eval_node(node.operand))
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Expr):
            return cls._eval_node(node.value)
        raise ValueError("Nicht unterstützter Ausdrucksteil")


class CalculatorApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Rechner")
        self.root.overrideredirect(True)  # custom titlebar
        self.root.resizable(True, True)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.colors = {
            "bg": "#0f172a",
            "panel": "#111827",
            "btn": "#1f2937",
            "btn_text": "#e2e8f0",
            "btn_active": "#22d3ee",
            "btn_active_fg": "#0b1223",
            "accent": "#22d3ee",
            "display_bg": "#0b1223",
            "display_fg": "#e2e8f0",
            "history_bg": "#0b1223",
            "history_fg": "#e2e8f0",
            "history_sel_bg": "#22d3ee",
            "history_sel_fg": "#0b1223",
            "muted": "#94a3b8",
            "title": "#0b1223",
            "title_text": "#e2e8f0",
            "title_hover": "#1f2937",
            "close_hover": "#ef4444",
        }
        self.root.configure(bg=self.colors["bg"])
        self._apply_dark_titlebar()

        self.is_maximized = False
        self._drag_offset: tuple[int, int] | None = None
        self.live_result_var = tk.StringVar(value="")
        self.history: list[tuple[str, str]] = []  # (expression, result_string)
        self.normal_geometry = ""
        self._build_titlebar()
        self._build_ui()
        self._bind_keys()

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=16, pady=16, bg=self.colors["bg"])
        container.grid(row=1, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=3)
        container.grid_columnconfigure(1, weight=2)
        container.grid_rowconfigure(0, weight=1)

        calc_frame = tk.Frame(container, bg=self.colors["panel"], bd=0, highlightthickness=0)
        calc_frame.grid(row=0, column=0, sticky="nsew")
        for i in range(4):
            calc_frame.grid_columnconfigure(i, weight=1)

        display = tk.Text(
            calc_frame,
            font=("Segoe UI", 18),
            height=3,
            wrap="char",
            width=18,
            bd=0,
            relief="flat",
            bg=self.colors["display_bg"],
            fg=self.colors["display_fg"],
            insertbackground=self.colors["accent"],
            highlightthickness=2,
            highlightcolor=self.colors["accent"],
            highlightbackground=self.colors["panel"],
            padx=8,
            pady=8,
        )
        display.grid(row=0, column=0, columnspan=4, pady=(0, 12), sticky="nsew")
        display.focus_set()
        self.display = display

        live_label = tk.Label(
            calc_frame,
            textvariable=self.live_result_var,
            font=("Segoe UI", 12),
            fg=self.colors["accent"],
            bg=self.colors["display_bg"],
            anchor="e",
            padx=8,
            pady=4,
        )
        live_label.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(0, 12))

        buttons = [
            [
                ("C", self.clear),
                ("←", self.backspace),
                ("(", lambda: self.append("(")),
                (")", lambda: self.append(")")),
            ],
            [
                ("1/x", self.apply_reciprocal),
                ("√", self.apply_sqrt),
                ("x²", self.apply_square),
                ("%", self.apply_percent),
            ],
            [
                ("7", lambda: self.append("7")),
                ("8", lambda: self.append("8")),
                ("9", lambda: self.append("9")),
                ("/", lambda: self.append("/")),
            ],
            [
                ("4", lambda: self.append("4")),
                ("5", lambda: self.append("5")),
                ("6", lambda: self.append("6")),
                ("*", lambda: self.append("*")),
            ],
            [
                ("1", lambda: self.append("1")),
                ("2", lambda: self.append("2")),
                ("3", lambda: self.append("3")),
                ("-", lambda: self.append("-")),
            ],
            [
                ("±", self.negate),
                ("0", lambda: self.append("0")),
                (",", lambda: self.append(",")),
                ("+", lambda: self.append("+")),
            ],
            [
                ("=", self.evaluate),
            ],
        ]

        common_btn = {
            "font": ("Segoe UI", 14, "bold"),
            "width": 4,
            "height": 2,
            "bg": self.colors["btn"],
            "fg": self.colors["btn_text"],
            "activebackground": self.colors["btn_active"],
            "activeforeground": self.colors["btn_active_fg"],
            "bd": 0,
            "relief": "flat",
            "highlightthickness": 0,
            "cursor": "hand2",
        }

        for r, row in enumerate(buttons, start=2):
            for c, (label, command) in enumerate(row):
                colspan = 4 if label == "=" else 1
                btn_style = dict(common_btn)
                if label == "=":
                    btn_style["bg"] = self.colors["accent"]
                    btn_style["fg"] = self.colors["btn_active_fg"]
                    btn_style["activebackground"] = self.colors["btn_active"]
                btn = tk.Button(calc_frame, text=label, command=command, **btn_style)
                btn.grid(row=r, column=c, columnspan=colspan, sticky="nsew", padx=2, pady=2)
                if label == "=":
                    break

        for i in range(len(buttons) + 2):
            calc_frame.grid_rowconfigure(i, weight=1)

        history_frame = tk.Frame(container, padx=16, bg=self.colors["bg"])
        history_frame.grid(row=0, column=1, sticky="nsew")
        history_frame.grid_rowconfigure(1, weight=1)
        history_frame.grid_columnconfigure(0, weight=1)
        tk.Label(
            history_frame,
            text="Historie",
            font=("Segoe UI", 12, "bold"),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
        ).pack(anchor="w")

        history_container = tk.Frame(history_frame, bg=self.colors["panel"], bd=0, highlightthickness=0)
        history_container.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(
            history_container,
            orient="vertical",
            bg=self.colors["btn"],
            activebackground=self.colors["btn_active"],
            troughcolor=self.colors["panel"],
            highlightthickness=0,
            bd=0,
            width=12,
            relief="flat",
        )
        scrollbar.pack(side="right", fill="y")

        self.history_listbox = tk.Listbox(
            history_container,
            height=12,
            width=22,
            font=("Segoe UI", 11),
            activestyle="dotbox",
            exportselection=False,
            yscrollcommand=scrollbar.set,
            bg=self.colors["history_bg"],
            fg=self.colors["history_fg"],
            selectbackground=self.colors["history_sel_bg"],
            selectforeground=self.colors["history_sel_fg"],
            highlightthickness=0,
            relief="flat",
        )
        self.history_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.history_listbox.yview)

        self.history_listbox.bind("<Double-Button-1>", self._recall_history)

    def _bind_keys(self) -> None:
        # Bind both root and entry to ensure numpad input does not fall through to default Entry insert
        self.root.bind("<Key>", self._handle_key)
        self.display.bind("<Key>", self._handle_key)
        self.root.bind("<Return>", self._handle_return)
        self.root.bind("<KP_Enter>", self._handle_return)
        self.root.bind("<BackSpace>", self._handle_backspace)
        self.root.bind("<Delete>", self._handle_clear)
        self.root.bind("<Escape>", self._handle_clear)
        # Drag and titlebar actions
        self.titlebar.bind("<ButtonPress-1>", self._start_move)
        self.titlebar.bind("<B1-Motion>", self._on_move)
        self.titlebar.bind("<Double-Button-1>", self._toggle_maximize)

    def append(self, value: str) -> None:
        current = self._get_display()
        self._set_display(current + value)

    def clear(self) -> None:
        self._set_display("")

    def backspace(self) -> None:
        current = self._get_display()
        self._set_display(current[:-1])

    def negate(self) -> None:
        current = self._get_display().strip()
        if not current:
            self._set_display("-")
            return
        if current.startswith("-"):
            self._set_display(current[1:])
        else:
            self._set_display("-" + current)

    def evaluate(self) -> None:
        expression = self._get_display().strip()
        try:
            result = SafeEvaluator.evaluate(expression)
            display_value = self._format_number(result)
            self._set_display(display_value)
            self._add_to_history(expression, display_value)
        except ZeroDivisionError:
            messagebox.showerror("Fehler", "Division durch 0 ist nicht erlaubt")
        except ValueError as exc:
            messagebox.showerror("Fehler", str(exc))

    def apply_sqrt(self) -> None:
        self._apply_unary(math.sqrt, "Wurzel aus einer negativen Zahl ist nicht definiert")

    def apply_reciprocal(self) -> None:
        def op(x: float) -> float:
            if x == 0:
                raise ZeroDivisionError
            return 1 / x

        self._apply_unary(op, "Division durch 0 ist nicht erlaubt")

    def apply_square(self) -> None:
        self._apply_unary(lambda x: x * x)

    def apply_percent(self) -> None:
        self._apply_unary(lambda x: x / 100)

    def _get_display(self) -> str:
        return self.display.get("1.0", "end-1c")

    def _set_display(self, value: str) -> None:
        self.display.delete("1.0", "end")
        self.display.insert("1.0", value)
        self.display.mark_set("insert", "end")
        self._refresh_live_result()

    def _refresh_live_result(self) -> None:
        expression = self._get_display().strip()
        if not expression:
            self.live_result_var.set("")
            return
        try:
            result = SafeEvaluator.evaluate(expression)
            self.live_result_var.set(self._format_number(result))
        except Exception:
            self.live_result_var.set("…")

    def _apply_unary(self, func, error_msg: str | None = None) -> None:
        expression = self._get_display().strip()
        if not expression:
            return
        try:
            value = SafeEvaluator.evaluate(expression)
            new_value = func(value)
            self._set_display(self._format_number(new_value))
        except ZeroDivisionError:
            messagebox.showerror("Fehler", "Division durch 0 ist nicht erlaubt")
        except ValueError:
            messagebox.showerror("Fehler", error_msg or "Ungültige Operation")
        except Exception as exc:
            messagebox.showerror("Fehler", str(exc))

    def _format_number(self, value: float) -> str:
        """Format numbers with space as thousands separator and comma as decimal."""
        if value.is_integer():
            return f"{int(value):,}".replace(",", " ")

        text = f"{value:.12g}"
        if "e" in text or "E" in text:
            return text  # leave scientific notation unchanged

        sign = ""
        if text.startswith("-"):
            sign = "-"
            text = text[1:]

        int_part, _, frac_part = text.partition(".")
        grouped_int = f"{int(int_part or '0'):,}".replace(",", " ")
        if frac_part:
            return f"{sign}{grouped_int},{frac_part}"
        return f"{sign}{grouped_int}"

    def _add_to_history(self, expression: str, result_str: str) -> None:
        if not expression:
            return
        self.history.insert(0, (expression, result_str))
        self.history_listbox.insert(0, f"{expression} = {result_str}")

    def _recall_history(self, event=None) -> None:  # noqa: D401 - simple handler
        selection = self.history_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx >= len(self.history):
            return
        expression, _ = self.history[idx]
        self._set_display(expression)

    def _build_titlebar(self) -> None:
        self.titlebar = tk.Frame(self.root, bg=self.colors["title"], height=32, bd=0, highlightthickness=0)
        self.titlebar.grid(row=0, column=0, sticky="ew")
        self.titlebar.grid_columnconfigure(0, weight=1)

        title_label = tk.Label(
            self.titlebar,
            text="Rechner",
            fg=self.colors["title_text"],
            bg=self.colors["title"],
            font=("Segoe UI", 10, "bold"),
            padx=10,
        )
        title_label.grid(row=0, column=0, sticky="w")

        btn_frame = tk.Frame(self.titlebar, bg=self.colors["title"], bd=0)
        btn_frame.grid(row=0, column=1, sticky="e")

        def mk_btn(txt, command, hover_bg=None):
            b = tk.Button(
                btn_frame,
                text=txt,
                command=command,
                bd=0,
                width=4,
                bg=self.colors["title"],
                fg=self.colors["title_text"],
                activebackground=hover_bg or self.colors["title_hover"],
                activeforeground=self.colors["title_text"],
                relief="flat",
                highlightthickness=0,
                cursor="hand2",
                font=("Segoe UI", 10, "bold"),
            )
            b.bind("<Enter>", lambda e, btn=b, bg=hover_bg: btn.configure(bg=bg or self.colors["title_hover"]))
            b.bind("<Leave>", lambda e, btn=b: btn.configure(bg=self.colors["title"]))
            return b

        mk_btn("—", self._do_minimize).pack(side="left", padx=2, pady=4)
        mk_btn("✕", self._do_close, hover_bg=self.colors["close_hover"]).pack(side="left", padx=(2, 6), pady=4)

        # size grip for manual resize
        grip = ttk.Sizegrip(self.root)
        grip.grid(row=2, column=0, sticky="se")
        grip.bind("<B1-Motion>", self._resize_from_grip)

    def _apply_dark_titlebar(self) -> None:
        """Try to apply a dark titlebar on Windows 10/11 to match the theme."""
        try:
            if sys.platform != "win32":
                return
            hwnd = self.root.winfo_id()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            if res != 0:  # fallback for older builds
                DWMWA_USE_IMMERSIVE_DARK_MODE = 19
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    wintypes.HWND(hwnd),
                    wintypes.DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE),
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                )
        except Exception:
            # Best-effort: ignore if unavailable
            pass

    def _start_move(self, event) -> None:
        self._drag_offset = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def _on_move(self, event) -> None:
        if not self._drag_offset or self.is_maximized:
            return
        dx = event.x_root - self._drag_offset[0]
        dy = event.y_root - self._drag_offset[1]
        new_x = self._drag_offset[2] + dx
        new_y = self._drag_offset[3] + dy
        self.root.geometry(f"+{new_x}+{new_y}")

    def _toggle_maximize(self, event=None) -> None:  # noqa: D401
        if self.is_maximized:
            self.root.geometry(self.normal_geometry or "800x500+100+100")
            self.is_maximized = False
        else:
            self.normal_geometry = self.root.geometry()
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()
            self.root.geometry(f"{w}x{h}+0+0")
            self.is_maximized = True

    def _do_minimize(self) -> None:
        self.root.update_idletasks()
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.after(10, lambda: self.root.overrideredirect(True))

    def _do_close(self) -> None:
        self.root.destroy()

    def _resize_from_grip(self, event) -> None:
        if self.is_maximized:
            return
        x = self.root.winfo_pointerx() - self.root.winfo_rootx()
        y = self.root.winfo_pointery() - self.root.winfo_rooty()
        new_w = max(400, x)
        new_h = max(400, y)
        self.root.geometry(f"{new_w}x{new_h}")

    def _handle_key(self, event) -> None:
        if event.char in "0123456789,+-*/()":
            self.append(event.char)
            return "break"
        if event.char == ".":
            self.append(",")
            return "break"

    def _handle_return(self, event) -> str:
        self.evaluate()
        return "break"

    def _handle_backspace(self, event) -> str:
        self.backspace()
        return "break"

    def _handle_clear(self, event) -> str:
        self.clear()
        return "break"

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = CalculatorApp()
    app.run()


if __name__ == "__main__":
    main()
