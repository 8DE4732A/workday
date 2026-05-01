"""时间线视图"""
import threading
import io
import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from typing import List
from PIL import Image

from workday.core.logger import get_logger
from workday.gui.widgets.date_nav import DateNav
from workday.gui.widgets.activity_card import ActivityCard

logger = get_logger(__name__)


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
        self._detail = DetailPanel(content, db=self.db)
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
    """卡片详情面板（含视频播放）"""

    _VIDEO_W = 480
    _VIDEO_H = 270

    def __init__(self, parent, db=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self._playing = False
        self._stop_flag = False
        self._thread: threading.Thread | None = None
        self._build_empty()

    def _build_empty(self):
        self._placeholder = ctk.CTkLabel(
            self, text="选择左侧活动卡片查看详情",
            font=("", 14), text_color=("gray50", "gray60")
        )
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._content = None

    def clear(self):
        self._stop_playback()
        if self._content:
            self._content.destroy()
            self._content = None
        self._scroll.pack_forget()
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def show(self, card):
        self._stop_playback()
        self._placeholder.place_forget()
        if self._content:
            self._content.destroy()

        self._scroll.pack(fill="both", expand=True, padx=20, pady=16)
        self._content = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

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

        # 视频播放区
        self._build_video_section(card)

        # 描述
        if card.description:
            ctk.CTkLabel(self._content, text="描述", font=("", 12, "bold"),
                         anchor="w").pack(fill="x", pady=(12, 0))
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

    def _build_video_section(self, card):
        """构建视频播放区域"""
        chunks = []
        if self.db:
            try:
                all_chunks = self.db.get_chunks_by_time_range(card.start_ts, card.end_ts)
                chunks = [c for c in all_chunks if c.file_path]
            except Exception:
                pass

        video_frame = ctk.CTkFrame(self._content, fg_color=("gray85", "gray20"), corner_radius=8)
        video_frame.pack(fill="x", pady=(0, 8))

        if not chunks:
            ctk.CTkLabel(video_frame, text="暂无视频片段",
                         font=("", 12), text_color=("gray50", "gray60")).pack(pady=20)
            return

        # 视频画面容器 - 固定尺寸
        canvas_frame = tk.Frame(video_frame, width=self._VIDEO_W, height=self._VIDEO_H, bg="#111111")
        canvas_frame.pack(pady=(8, 4))
        canvas_frame.pack_propagate(False)

        # 用原生 tk.Label 避免 CTkLabel 图片渲染问题
        self._video_label = tk.Label(canvas_frame, bg="#111111")
        self._video_label.place(relx=0.5, rely=0.5, anchor="center")

        # 进度信息
        self._progress_label = ctk.CTkLabel(
            video_frame, text=f"共 {len(chunks)} 个片段",
            font=("", 11), text_color=("gray50", "gray60")
        )
        self._progress_label.pack()

        # 控制按钮
        ctrl = ctk.CTkFrame(video_frame, fg_color="transparent")
        ctrl.pack(pady=(4, 8))

        self._play_btn = ctk.CTkButton(
            ctrl, text="▶ 播放", width=80, height=28,
            command=lambda: self._toggle_playback(chunks)
        )
        self._play_btn.pack(side="left", padx=4)
        ctk.CTkButton(
            ctrl, text="■ 停止", width=80, height=28,
            fg_color=("gray70", "gray35"), hover_color=("gray60", "gray30"),
            command=self._stop_playback
        ).pack(side="left", padx=4)

    def _toggle_playback(self, chunks):
        if self._playing:
            self._stop_playback()
        else:
            self._start_playback(chunks)

    def _start_playback(self, chunks):
        self._stop_flag = False
        self._playing = True
        if hasattr(self, '_play_btn'):
            self._play_btn.configure(text="⏸ 暂停")
        self._thread = threading.Thread(target=self._play_thread, args=(chunks,), daemon=True)
        self._thread.start()

    def _stop_playback(self):
        self._stop_flag = True
        self._playing = False
        if hasattr(self, '_play_btn'):
            try:
                self._play_btn.configure(text="▶ 播放")
            except Exception:
                pass

    def _play_thread(self, chunks):
        import cv2
        for i, chunk in enumerate(chunks):
            if self._stop_flag:
                break
            cap = cv2.VideoCapture(chunk.file_path)
            if not cap.isOpened():
                logger.warning(f"Cannot open video: {chunk.file_path}")
                continue

            fps = cap.get(cv2.CAP_PROP_FPS) or 1.0
            delay = max(0.033, 1.0 / fps)  # 至少 30ms，防止除零
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_idx = 0

            while not self._stop_flag:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_idx += 1

                # BGR -> RGB，缩放到适合尺寸
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]
                scale = min(self._VIDEO_W / w, self._VIDEO_H / h)
                new_w, new_h = int(w * scale), int(h * scale)
                resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
                img = Image.fromarray(resized)

                progress_text = f"片段 {i+1}/{len(chunks)}  帧 {frame_idx}/{frame_count}"
                try:
                    self._video_label.after(0, self._update_frame, img, progress_text)
                except Exception:
                    break
                threading.Event().wait(delay)
            cap.release()

        if not self._stop_flag:
            try:
                self._play_btn.after(0, lambda: self._play_btn.configure(text="▶ 播放"))
                self._progress_label.after(0, lambda: self._progress_label.configure(text="播放完毕"))
            except Exception:
                pass
        self._playing = False
        self._stop_flag = False

    def _update_frame(self, img: Image.Image, progress_text: str):
        """在主线程中更新视频帧（用 tk.PhotoImage 避免 ImageTk 兼容问题）"""
        try:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            photo = tk.PhotoImage(data=buf.read())
            self._video_label.configure(image=photo)
            self._photo_ref = photo  # 防止被 GC
            self._progress_label.configure(text=progress_text)
        except Exception:
            import traceback; traceback.print_exc()
