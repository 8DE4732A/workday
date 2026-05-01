"""仪表盘视图 - Token 用量统计"""
import customtkinter as ctk
from datetime import datetime, timezone


def _fmt_num(n: int) -> str:
    """数字加千位分隔符"""
    return f"{n:,}"


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
        # 标题
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(header, text="Token 用量仪表盘", font=("", 20, "bold")).pack(side="left")

        # 过滤区
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(filter_frame, text="开始日期：", font=("", 12)).pack(side="left")
        self._start_entry = ctk.CTkEntry(filter_frame, width=110, placeholder_text="YYYY-MM-DD")
        self._start_entry.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(filter_frame, text="结束日期：", font=("", 12)).pack(side="left")
        self._end_entry = ctk.CTkEntry(filter_frame, width=110, placeholder_text="YYYY-MM-DD")
        self._end_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(filter_frame, text="查询", width=60, height=28,
                      command=self._on_filter).pack(side="left", padx=(0, 4))
        ctk.CTkButton(filter_frame, text="全部", width=60, height=28,
                      command=self._clear_filter).pack(side="left")

        # 汇总统计卡片区
        self._summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._summary_frame.pack(fill="x", padx=16, pady=(0, 8))
        self._summary_cards: list[ctk.CTkFrame] = []
        self._build_summary_cards()

        # 表格头
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
        """构建三个汇总卡片：输入 / 输出 / 总计"""
        defs = [
            ("输入 Token", "prompt"),
            ("输出 Token", "completion"),
            ("总计 Token", "total"),
        ]
        for title, key in defs:
            card = ctk.CTkFrame(self._summary_frame, corner_radius=8,
                                fg_color=("gray90", "gray18"))
            card.pack(side="left", padx=(0, 8), pady=2, ipadx=12, ipady=8)
            ctk.CTkLabel(card, text=title, font=("", 11),
                         text_color=("gray50", "gray55")).pack(anchor="w")
            val_label = ctk.CTkLabel(card, text="—", font=("", 20, "bold"))
            val_label.pack(anchor="w")
            card._key = key          # type: ignore[attr-defined]
            card._val_label = val_label  # type: ignore[attr-defined]
            self._summary_cards.append(card)

    def _update_summary(self, summary: dict):
        for card in self._summary_cards:
            key = card._key          # type: ignore[attr-defined]
            lbl = card._val_label    # type: ignore[attr-defined]
            lbl.configure(text=_fmt_num(summary.get(f"{key}_tokens", 0)))

    def _render_header(self):
        cols = [("时间", 140), ("类型", 100), ("模型", 150),
                ("输入 Token", 90), ("输出 Token", 90), ("总计", 80), ("批次 ID", 70)]
        for text, w in cols:
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
        """返回 (start_date, end_date)，单日查询时 start==end"""
        start = self._start_entry.get().strip() or None
        end = self._end_entry.get().strip() or None
        return start, end

    def _load(self):
        for w in self._table.winfo_children():
            w.destroy()

        start, end = self._get_filter()

        try:
            offset = self._page * self._page_size
            records = self.db.get_token_usage_records(
                start_date=start, end_date=end,
                limit=self._page_size, offset=offset
            )
            self._total = self.db.get_token_usage_count(start_date=start, end_date=end)
            summary = self.db.get_token_usage_summary(start_date=start, end_date=end)
            self._update_summary(summary)

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
                    corner_radius=0
                )
                row.pack(fill="x", pady=1)

                cols = [
                    (self._fmt_time(rec['created_at']), 140),
                    (rec['request_type'], 100),
                    (rec['model'][:20] if rec['model'] else "", 150),
                    (_fmt_num(rec['prompt_tokens']), 90),
                    (_fmt_num(rec['completion_tokens']), 90),
                    (_fmt_num(rec['total_tokens']), 80),
                    (str(rec['batch_id']) if rec['batch_id'] else "-", 70),
                ]
                for text, w in cols:
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
        self._start_entry.delete(0, "end")
        self._end_entry.delete(0, "end")
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
