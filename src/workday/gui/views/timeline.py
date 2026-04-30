"""时间线视图"""
import customtkinter as ctk
from datetime import datetime
from typing import Optional, List

from workday.gui.widgets.date_nav import DateNav
from workday.gui.widgets.activity_card import ActivityCard, format_time, format_duration


class TimelineView(ctk.CTkFrame):
    """主时间线视图"""

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self._cards = []
        self._card_widgets: List[ActivityCard] = []
        self._selected_card = None
        self._build()
        self._load_cards(datetime.now().strftime("%Y-%m-%d"))

    def _build(self):
        # 顶部：日期导航
        self._date_nav = DateNav(
            self,
            on_date_change=self._load_cards,
            on_refresh=lambda: self._load_cards(self._date_nav.current_date_str)
        )
        self._date_nav.pack(fill="x", padx=16, pady=(12, 8))

        # 分隔线
        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).pack(fill="x")

        # 主内容区
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=0, pady=0)
        content.grid_columnconfigure(0, weight=0, minsize=380)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # 左：卡片列表
        left = ctk.CTkFrame(content, width=380, fg_color=("gray96", "gray13"))
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)

        self._status_label = ctk.CTkLabel(left, text="加载中...", font=("", 12),
                                           text_color=("gray50", "gray60"))
        self._status_label.pack(pady=8)

        self._card_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self._card_list.pack(fill="both", expand=True, padx=8, pady=4)

        # 右：详情面板
        self._detail = DetailPanel(content)
        self._detail.grid(row=0, column=1, sticky="nsew", padx=0)

    def _load_cards(self, day: str):
        self._status_label.configure(text="加载中...")
        for w in self._card_widgets:
            w.destroy()
        self._card_widgets.clear()
        self._selected_card = None
        self._detail.clear()

        try:
            self._cards = self.db.get_timeline_cards_by_day(day)
        except Exception as e:
            self._status_label.configure(text=f"加载失败: {e}")
            return

        if not self._cards:
            self._status_label.configure(text="暂无数据")
            return

        self._status_label.configure(text=f"共 {len(self._cards)} 条活动")

        for card in self._cards:
            widget = ActivityCard(
                self._card_list,
                card,
                on_click=self._on_card_click,
                fg_color=("gray92", "gray17")
            )
            widget.pack(fill="x", pady=4)
            self._card_widgets.append(widget)

    def _on_card_click(self, card):
        # 取消之前选中
        for w in self._card_widgets:
            w.set_selected(w.card is card)
        self._selected_card = card
        self._detail.show(card)

    def refresh(self):
        if hasattr(self, '_date_nav'):
            self._load_cards(self._date_nav.current_date_str)


class DetailPanel(ctk.CTkFrame):
    """卡片详情面板"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_empty()

    def _build_empty(self):
        self._placeholder = ctk.CTkLabel(
            self, text="选择左侧活动卡片查看详情",
            font=("", 14), text_color=("gray50", "gray60")
        )
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self._content = None

    def clear(self):
        if self._content:
            self._content.destroy()
            self._content = None
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def show(self, card):
        if self._content:
            self._content.destroy()
        self._placeholder.place_forget()

        self._content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True, padx=20, pady=16)

        from workday.gui.widgets.activity_card import CATEGORY_COLORS, format_time, format_duration

        cat = card.category or "其他"
        color = CATEGORY_COLORS.get(cat, "#6b7280")

        # 分类 + 时长
        top = ctk.CTkFrame(self._content, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(top, text=f"  {cat}  ", font=("", 12),
                     fg_color=color, corner_radius=4, text_color="white").pack(side="left")
        dur = format_duration(card.duration)
        ctk.CTkLabel(top, text=dur, font=("", 12),
                     text_color=("gray50", "gray60")).pack(side="right")

        # 标题
        ctk.CTkLabel(self._content, text=card.title, font=("", 18, "bold"),
                     anchor="w", wraplength=500).pack(fill="x", pady=(0, 6))

        # 时间范围
        time_str = f"{format_time(card.start_ts)}  –  {format_time(card.end_ts)}"
        ctk.CTkLabel(self._content, text=time_str, font=("", 13),
                     text_color=("gray50", "gray60"), anchor="w").pack(fill="x", pady=(0, 12))

        # 分隔线
        ctk.CTkFrame(self._content, height=1, fg_color=("gray80", "gray30")).pack(fill="x", pady=(0, 12))

        # 描述
        if card.description:
            ctk.CTkLabel(self._content, text="描述", font=("", 12, "bold"),
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(self._content, text=card.description, font=("", 13),
                         anchor="w", justify="left", wraplength=500).pack(fill="x", pady=(4, 12))

        # 元数据
        ctk.CTkFrame(self._content, height=1, fg_color=("gray80", "gray30")).pack(fill="x", pady=(0, 8))
        meta_items = [
            ("批次 ID", str(card.batch_id)),
            ("卡片 ID", str(card.id)),
            ("开始时间", str(card.start_ts)),
            ("结束时间", str(card.end_ts)),
        ]
        for label, value in meta_items:
            row = ctk.CTkFrame(self._content, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=label, font=("", 11), width=80,
                         text_color=("gray50", "gray60"), anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value, font=("", 11), anchor="w").pack(side="left")
