"""仪表盘视图 - Token 用量统计"""
import customtkinter as ctk
from datetime import datetime


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
        # 标题区
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(header, text="Token 用量仪表盘", font=("", 20, "bold")).pack(side="left")

        # 日期过滤
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(filter_frame, text="日期过滤：", font=("", 12)).pack(side="left")
        self._date_entry = ctk.CTkEntry(filter_frame, width=120, placeholder_text="YYYY-MM-DD")
        self._date_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(filter_frame, text="查询", width=60, height=28,
                      command=self._on_filter).pack(side="left", padx=(0, 8))
        ctk.CTkButton(filter_frame, text="全部", width=60, height=28,
                      command=self._clear_filter).pack(side="left")

        self._summary_label = ctk.CTkLabel(filter_frame, text="",
                                            font=("", 12), text_color=("gray50", "gray60"))
        self._summary_label.pack(side="right")

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

    def _render_header(self):
        cols = [("时间", 140), ("类型", 80), ("模型", 140),
                ("输入 Token", 90), ("输出 Token", 90), ("总计", 70), ("批次 ID", 70)]
        for text, w in cols:
            ctk.CTkLabel(self._header_frame, text=text, font=("", 12, "bold"),
                         width=w, anchor="w").pack(side="left", padx=4, pady=4)

    def _load(self, date: str = None):
        for w in self._table.winfo_children():
            w.destroy()

        try:
            offset = self._page * self._page_size
            records = self.db.get_token_usage_records(date=date, limit=self._page_size, offset=offset)
            self._total = self.db.get_token_usage_count(date=date)

            if not records:
                ctk.CTkLabel(self._table, text="暂无数据", font=("", 13),
                             text_color=("gray50", "gray60")).pack(pady=40)
                self._summary_label.configure(text="共 0 条记录")
                self._update_pagination()
                return

            self._summary_label.configure(text=f"共 {self._total} 条记录")

            for i, rec in enumerate(records):
                row = ctk.CTkFrame(
                    self._table,
                    fg_color=("gray95", "gray15") if i % 2 == 0 else ("gray90", "gray18"),
                    corner_radius=0
                )
                row.pack(fill="x", pady=1)

                cols = [
                    (rec['created_at'][:16] if rec['created_at'] else "", 140),
                    (rec['request_type'], 80),
                    (rec['model'][:18], 140),
                    (str(rec['prompt_tokens']), 90),
                    (str(rec['completion_tokens']), 90),
                    (str(rec['total_tokens']), 70),
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
        date = self._date_entry.get().strip() or None
        self._load(date=date)

    def _clear_filter(self):
        self._date_entry.delete(0, "end")
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
            date = self._date_entry.get().strip() or None
            self._load(date=date)

    def _next_page(self):
        total_pages = (self._total + self._page_size - 1) // self._page_size
        if self._page < total_pages - 1:
            self._page += 1
            date = self._date_entry.get().strip() or None
            self._load(date=date)

    def refresh(self):
        self._load()
