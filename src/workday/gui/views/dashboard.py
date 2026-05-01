"""仪表盘视图 - Token 用量统计"""
import calendar
import customtkinter as ctk
from datetime import datetime, timezone, date


def _fmt_num(n: int) -> str:
    return f"{n:,}"


class _CalendarPicker(ctk.CTkToplevel):
    """轻量日历弹窗，选完后回调 on_select(date_str)"""

    def __init__(self, parent, on_select, initial: str = ""):
        super().__init__(parent)
        self.on_select = on_select
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

        # 定位到父控件旁边
        self.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty() + parent.winfo_height() + 2
        self.geometry(f"+{px}+{py}")

        # 点击窗口外关闭
        self.bind("<FocusOut>", lambda e: self.after(100, self._check_focus))

    def _check_focus(self):
        try:
            focused = self.focus_get()
            if focused is None or str(focused) not in str(self.winfo_children()):
                self.destroy()
        except Exception:
            self.destroy()

    def _build(self):
        self._top = ctk.CTkFrame(self, corner_radius=8, fg_color=("gray92", "gray18"),
                                 border_width=1, border_color=("gray75", "gray35"))
        self._top.pack(padx=1, pady=1)

        # 月份导航
        nav = ctk.CTkFrame(self._top, fg_color="transparent")
        nav.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkButton(nav, text="◀", width=28, height=26,
                      command=self._prev_month).pack(side="left")
        self._title = ctk.CTkLabel(nav, text="", font=("", 13, "bold"), width=130)
        self._title.pack(side="left", expand=True)
        ctk.CTkButton(nav, text="▶", width=28, height=26,
                      command=self._next_month).pack(side="right")

        # 星期头
        week_frame = ctk.CTkFrame(self._top, fg_color="transparent")
        week_frame.pack(padx=8)
        for d in ["一", "二", "三", "四", "五", "六", "日"]:
            ctk.CTkLabel(week_frame, text=d, font=("", 11),
                         width=32, text_color=("gray50", "gray55")).pack(side="left")

        # 日期格子容器
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

    def _prev_month(self):
        if self._month == 1:
            self._year -= 1
            self._month = 12
        else:
            self._month -= 1
        self._render()

    def _next_month(self):
        if self._month == 12:
            self._year += 1
            self._month = 1
        else:
            self._month += 1
        self._render()

    def _pick(self, d: date):
        self.on_select(d.isoformat())
        self.destroy()


class _DateButton(ctk.CTkFrame):
    """带日历弹窗的日期选择控件"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._value = ""
        self._picker: _CalendarPicker | None = None

        self._entry = ctk.CTkEntry(self, width=108, placeholder_text="YYYY-MM-DD",
                                   font=("", 12))
        self._entry.pack(side="left")
        ctk.CTkButton(self, text="📅", width=28, height=28,
                      font=("", 13), fg_color="transparent",
                      hover_color=("gray80", "gray30"),
                      command=self._open_picker).pack(side="left", padx=(2, 0))

    def _open_picker(self):
        if self._picker and self._picker.winfo_exists():
            self._picker.destroy()
            self._picker = None
            return
        current = self._entry.get().strip()
        self._picker = _CalendarPicker(self._entry, on_select=self._on_select,
                                       initial=current)
        self._picker.focus_set()

    def _on_select(self, date_str: str):
        self._entry.delete(0, "end")
        self._entry.insert(0, date_str)
        self._picker = None

    def get(self) -> str:
        return self._entry.get().strip()

    def clear(self):
        self._entry.delete(0, "end")


class DashboardView(ctk.CTkFrame):
    """Token 用量仪表盘"""

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self._page = 0
        self._page_size = 20
        self._total = 0
        self._build()
        self._load()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(header, text="Token 用量仪表盘", font=("", 20, "bold")).pack(side="left")

        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(filter_frame, text="开始日期：", font=("", 12)).pack(side="left")
        self._start_picker = _DateButton(filter_frame)
        self._start_picker.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(filter_frame, text="结束日期：", font=("", 12)).pack(side="left")
        self._end_picker = _DateButton(filter_frame)
        self._end_picker.pack(side="left", padx=(0, 12))

        ctk.CTkButton(filter_frame, text="查询", width=60, height=28,
                      command=self._on_filter).pack(side="left", padx=(0, 4))
        ctk.CTkButton(filter_frame, text="全部", width=60, height=28,
                      command=self._clear_filter).pack(side="left")

        # 汇总卡片
        self._summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._summary_frame.pack(fill="x", padx=16, pady=(0, 8))
        self._summary_cards: list[ctk.CTkFrame] = []
        self._build_summary_cards()

        # 表头
        self._header_frame = ctk.CTkFrame(self, corner_radius=0,
                                          fg_color=("gray85", "gray25"))
        self._header_frame.pack(fill="x", padx=16)
        self._render_header()

        # 数据区
        self._table = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._table.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # 分页
        page_frame = ctk.CTkFrame(self, fg_color="transparent")
        page_frame.pack(fill="x", padx=16, pady=(0, 12))
        self._prev_btn = ctk.CTkButton(page_frame, text="◀ 上一页", width=90, height=28,
                                       command=self._prev_page)
        self._prev_btn.pack(side="left", padx=(0, 8))
        self._page_label = ctk.CTkLabel(page_frame, text="第 1 页", font=("", 12))
        self._page_label.pack(side="left", padx=8)
        self._next_btn = ctk.CTkButton(page_frame, text="下一页 ▶", width=90, height=28,
                                       command=self._next_page)
        self._next_btn.pack(side="left", padx=8)
        self._count_label = ctk.CTkLabel(page_frame, text="",
                                         font=("", 12), text_color=("gray50", "gray60"))
        self._count_label.pack(side="right")

    def _build_summary_cards(self):
        for title, key in [("输入 Token", "prompt"), ("输出 Token", "completion"), ("总计 Token", "total")]:
            card = ctk.CTkFrame(self._summary_frame, corner_radius=8,
                                fg_color=("gray90", "gray18"))
            card.pack(side="left", padx=(0, 8), pady=2, ipadx=12, ipady=8)
            ctk.CTkLabel(card, text=title, font=("", 11),
                         text_color=("gray50", "gray55")).pack(anchor="w")
            val_label = ctk.CTkLabel(card, text="—", font=("", 20, "bold"))
            val_label.pack(anchor="w")
            card._key = key              # type: ignore[attr-defined]
            card._val_label = val_label  # type: ignore[attr-defined]
            self._summary_cards.append(card)

    def _update_summary(self, summary: dict):
        for card in self._summary_cards:
            card._val_label.configure(  # type: ignore[attr-defined]
                text=_fmt_num(summary.get(f"{card._key}_tokens", 0)))  # type: ignore[attr-defined]

    def _render_header(self):
        for text, w in [("时间", 140), ("类型", 100), ("模型", 150),
                        ("输入 Token", 90), ("输出 Token", 90), ("总计", 80), ("批次 ID", 70)]:
            ctk.CTkLabel(self._header_frame, text=text, font=("", 12, "bold"),
                         width=w, anchor="w").pack(side="left", padx=4, pady=4)

    def _fmt_time(self, utc_str: str) -> str:
        if not utc_str:
            return ""
        try:
            dt = datetime.fromisoformat(utc_str).replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            return utc_str[:16]

    def _get_filter(self):
        start = self._start_picker.get() or None
        end = self._end_picker.get() or None
        return start, end

    def _load(self):
        for w in self._table.winfo_children():
            w.destroy()
        start, end = self._get_filter()
        try:
            offset = self._page * self._page_size
            records = self.db.get_token_usage_records(
                start_date=start, end_date=end, limit=self._page_size, offset=offset)
            self._total = self.db.get_token_usage_count(start_date=start, end_date=end)
            self._update_summary(self.db.get_token_usage_summary(start_date=start, end_date=end))
            self._count_label.configure(text=f"共 {self._total} 条记录")

            if not records:
                ctk.CTkLabel(self._table, text="暂无数据", font=("", 13),
                             text_color=("gray50", "gray60")).pack(pady=40)
                self._update_pagination()
                return

            for i, rec in enumerate(records):
                row = ctk.CTkFrame(
                    self._table,
                    fg_color=("gray95", "gray15") if i % 2 == 0 else ("gray90", "gray18"),
                    corner_radius=0)
                row.pack(fill="x", pady=1)
                for text, w in [
                    (self._fmt_time(rec['created_at']), 140),
                    (rec['request_type'], 100),
                    (rec['model'][:20] if rec['model'] else "", 150),
                    (_fmt_num(rec['prompt_tokens']), 90),
                    (_fmt_num(rec['completion_tokens']), 90),
                    (_fmt_num(rec['total_tokens']), 80),
                    (str(rec['batch_id']) if rec['batch_id'] else "-", 70),
                ]:
                    ctk.CTkLabel(row, text=text, font=("", 11),
                                 width=w, anchor="w").pack(side="left", padx=4, pady=3)
            self._update_pagination()
        except Exception as e:
            ctk.CTkLabel(self._table, text=f"加载失败: {e}", font=("", 12),
                         text_color="red").pack(pady=20)

    def _on_filter(self):
        self._page = 0
        self._load()

    def _clear_filter(self):
        self._start_picker.clear()
        self._end_picker.clear()
        self._page = 0
        self._load()

    def _update_pagination(self):
        total_pages = max(1, (self._total + self._page_size - 1) // self._page_size)
        self._page_label.configure(text=f"第 {self._page + 1} / {total_pages} 页")
        self._prev_btn.configure(state="normal" if self._page > 0 else "disabled")
        self._next_btn.configure(state="normal" if self._page < total_pages - 1 else "disabled")

    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._load()

    def _next_page(self):
        total_pages = (self._total + self._page_size - 1) // self._page_size
        if self._page < total_pages - 1:
            self._page += 1
            self._load()

    def refresh(self):
        self._load()
