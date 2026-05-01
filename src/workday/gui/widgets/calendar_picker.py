"""日历弹窗与日期选择控件"""
import calendar
import customtkinter as ctk
from datetime import date
from typing import Callable, Optional


class CalendarPicker(ctk.CTkToplevel):
    """轻量日历弹窗，选完后回调 on_select(date_str: str)"""

    def __init__(self, parent, on_select: Callable[[str], None], initial: str = ""):
        super().__init__(parent)
        self.on_select = on_select
        self._closed = False
        self.wm_overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(False, False)

        try:
            d = date.fromisoformat(initial)
        except Exception:
            d = date.today()
        self._year = d.year
        self._month = d.month

        self._build()
        self._render()

        self.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty() + parent.winfo_height() + 2
        self.geometry(f"+{px}+{py}")

        self._app = parent.winfo_toplevel()
        self._fid = self._app.bind("<ButtonPress>", self._on_root_click, add="+")

    def _on_root_click(self, event):
        try:
            if not self._closed and self.winfo_exists():
                x, y = event.x_root, event.y_root
                wx, wy = self.winfo_rootx(), self.winfo_rooty()
                ww, wh = self.winfo_width(), self.winfo_height()
                if not (wx <= x <= wx + ww and wy <= y <= wy + wh):
                    self._close()
        except Exception:
            self._close()

    def _close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._app.unbind("<ButtonPress>", self._fid)
        except Exception:
            pass
        try:
            if self.winfo_exists():
                self.destroy()
        except Exception:
            pass

    def _build(self):
        self._top = ctk.CTkFrame(self, corner_radius=8, fg_color=("gray92", "gray18"),
                                 border_width=1, border_color=("gray75", "gray35"))
        self._top.pack(padx=1, pady=1)

        nav = ctk.CTkFrame(self._top, fg_color="transparent")
        nav.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkButton(nav, text="◀", width=28, height=26,
                      command=self._prev_month).pack(side="left")
        self._title = ctk.CTkLabel(nav, text="", font=("", 13, "bold"), width=130)
        self._title.pack(side="left", expand=True)
        ctk.CTkButton(nav, text="▶", width=28, height=26,
                      command=self._next_month).pack(side="right")

        week_frame = ctk.CTkFrame(self._top, fg_color="transparent")
        week_frame.pack(padx=8)
        for d in ["一", "二", "三", "四", "五", "六", "日"]:
            ctk.CTkLabel(week_frame, text=d, font=("", 11),
                         width=32, text_color=("gray50", "gray55")).pack(side="left")

        self._grid = ctk.CTkFrame(self._top, fg_color="transparent")
        self._grid.pack(padx=8, pady=(0, 8))

    def _render(self):
        for w in self._grid.winfo_children():
            w.destroy()
        self._title.configure(text=f"{self._year} 年 {self._month} 月")

        cal = calendar.monthcalendar(self._year, self._month)
        today = date.today()
        for week in cal:
            row = ctk.CTkFrame(self._grid, fg_color="transparent")
            row.pack()
            for day in week:
                if day == 0:
                    ctk.CTkLabel(row, text="", width=32, height=28).pack(side="left")
                else:
                    d = date(self._year, self._month, day)
                    is_today = (d == today)
                    btn = ctk.CTkButton(
                        row, text=str(day), width=32, height=28,
                        font=("", 12, "bold") if is_today else ("", 12),
                        fg_color=("#3b82f6", "#2563eb") if is_today else "transparent",
                        hover_color=("gray80", "gray30"),
                        text_color=("gray10", "gray95"),
                        corner_radius=4,
                        command=lambda dd=d: self._pick(dd),
                    )
                    btn.pack(side="left")

    def _shift_month(self, delta: int):
        month = self._month + delta
        self._year += (month - 1) // 12
        self._month = (month - 1) % 12 + 1
        self._render()

    def _prev_month(self):
        self._shift_month(-1)

    def _next_month(self):
        self._shift_month(1)

    def _pick(self, d: date):
        self.on_select(d.isoformat())
        self._close()


class DateButton(ctk.CTkFrame):
    """带日历弹窗的日期选择控件，支持可选 on_change 回调"""

    def __init__(self, parent, on_change: Optional[Callable[[str], None]] = None,
                 initial: str = "", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_change = on_change
        self._picker: Optional[CalendarPicker] = None

        self._entry = ctk.CTkEntry(self, width=108, placeholder_text="YYYY-MM-DD",
                                   font=("", 12))
        self._entry.pack(side="left")
        if initial:
            self._entry.insert(0, initial)
        ctk.CTkButton(self, text="📅", width=28, height=28,
                      font=("", 13), fg_color="transparent",
                      hover_color=("gray80", "gray30"),
                      command=self._open_picker).pack(side="left", padx=(2, 0))

    def _open_picker(self):
        if self._picker and self._picker.winfo_exists():
            self._picker._close()
            self._picker = None
            return
        current = self._entry.get().strip()
        self._picker = CalendarPicker(self._entry, on_select=self._on_select, initial=current)
        self._picker.focus_set()

    def _on_select(self, date_str: str):
        self._entry.delete(0, "end")
        self._entry.insert(0, date_str)
        self._picker = None
        if self._on_change:
            self._on_change(date_str)

    def get(self) -> str:
        return self._entry.get().strip()

    def clear(self):
        self._entry.delete(0, "end")
