"""活动卡片组件"""
import customtkinter as ctk
from datetime import datetime
from typing import Callable, Optional

CATEGORY_COLORS = {
    "工作": "#3b82f6",
    "学习": "#10b981",
    "娱乐": "#f59e0b",
    "其他": "#6b7280",
}


def format_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def format_duration(seconds: float) -> str:
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"{minutes}分钟"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m" if mins else f"{hours}h"


class ActivityCard(ctk.CTkFrame):
    """活动卡片组件"""

    def __init__(self, parent, card, on_click: Optional[Callable] = None, **kwargs):
        super().__init__(parent, corner_radius=8, **kwargs)
        self.card = card
        self.on_click = on_click
        self._selected = False
        self._build()
        self.bind("<Button-1>", self._on_click)
        for widget in self.winfo_children():
            widget.bind("<Button-1>", self._on_click)

    def _build(self):
        self.configure(fg_color=("gray92", "gray17"))

        # 时间行
        time_frame = ctk.CTkFrame(self, fg_color="transparent")
        time_frame.pack(fill="x", padx=10, pady=(8, 2))

        time_str = f"{format_time(self.card.start_ts)} - {format_time(self.card.end_ts)}"
        ctk.CTkLabel(time_frame, text=time_str, font=("", 11),
                     text_color=("gray50", "gray60")).pack(side="left")

        dur_str = format_duration(self.card.duration)
        ctk.CTkLabel(time_frame, text=dur_str, font=("", 11),
                     text_color=("gray50", "gray60")).pack(side="right")

        # 标题
        ctk.CTkLabel(self, text=self.card.title, font=("", 13, "bold"),
                     anchor="w", wraplength=340).pack(fill="x", padx=10, pady=(0, 4))

        # 分类标签
        cat = self.card.category or "其他"
        color = CATEGORY_COLORS.get(cat, "#6b7280")
        cat_label = ctk.CTkLabel(self, text=f"  {cat}  ", font=("", 11),
                                 fg_color=color, corner_radius=4,
                                 text_color="white")
        cat_label.pack(anchor="w", padx=10, pady=(0, 8))

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self.configure(border_width=2, border_color=("#3b82f6", "#60a5fa"))
        else:
            self.configure(border_width=0)

    def _on_click(self, event=None):
        if self.on_click:
            self.on_click(self.card)
