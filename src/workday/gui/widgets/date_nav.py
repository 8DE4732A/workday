"""日期导航组件"""
import customtkinter as ctk
from datetime import datetime, timedelta
from typing import Callable, Optional


class DateNav(ctk.CTkFrame):
    """日期导航栏"""

    def __init__(self, parent, on_date_change: Optional[Callable] = None,
                 on_refresh: Optional[Callable] = None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_date_change = on_date_change
        self.on_refresh = on_refresh
        self._current_date = datetime.now().date()
        self._build()

    def _build(self):
        ctk.CTkButton(self, text="◀", width=32, height=32,
                      command=self._prev_day).pack(side="left", padx=(0, 4))

        self._date_label = ctk.CTkLabel(self, text=self._date_str(),
                                        font=("", 14, "bold"), width=120)
        self._date_label.pack(side="left", padx=4)

        ctk.CTkButton(self, text="▶", width=32, height=32,
                      command=self._next_day).pack(side="left", padx=(4, 8))

        ctk.CTkButton(self, text="今天", width=52, height=32,
                      command=self._go_today).pack(side="left", padx=4)

        ctk.CTkButton(self, text="↻ 刷新", width=64, height=32,
                      command=self._refresh).pack(side="left", padx=(8, 0))

    def _date_str(self) -> str:
        today = datetime.now().date()
        if self._current_date == today:
            return f"{self._current_date.strftime('%m-%d')} 今天"
        elif self._current_date == today - timedelta(days=1):
            return f"{self._current_date.strftime('%m-%d')} 昨天"
        return self._current_date.strftime("%Y-%m-%d")

    def _prev_day(self):
        self._current_date -= timedelta(days=1)
        self._update()

    def _next_day(self):
        next_day = self._current_date + timedelta(days=1)
        if next_day <= datetime.now().date():
            self._current_date = next_day
            self._update()

    def _go_today(self):
        self._current_date = datetime.now().date()
        self._update()

    def _refresh(self):
        if self.on_refresh:
            self.on_refresh()

    def _update(self):
        self._date_label.configure(text=self._date_str())
        if self.on_date_change:
            self.on_date_change(self._current_date.strftime("%Y-%m-%d"))

    @property
    def current_date_str(self) -> str:
        return self._current_date.strftime("%Y-%m-%d")
