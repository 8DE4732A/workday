"""录制控制组件"""
import customtkinter as ctk
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class RecordingControls(ctk.CTkFrame):
    """录制控制：开始/停止按钮 + 状态指示"""

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.db = db
        self._recorder_manager = None
        self._recording_thread = None
        self._build()
        self._poll_status()

    def _build(self):
        # 状态指示灯（Canvas 画圆）
        self._canvas = ctk.CTkCanvas(self, width=12, height=12,
                                     highlightthickness=0, bg=self._get_bg())
        self._canvas.pack(side="left", padx=(0, 6))
        self._dot = self._canvas.create_oval(2, 2, 10, 10, fill="#6b7280", outline="")

        self._btn = ctk.CTkButton(self, text="开始录制", width=90, height=32,
                                  command=self._toggle)
        self._btn.pack(side="left")

    def _get_bg(self):
        return ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1 if ctk.get_appearance_mode() == "Dark" else 0]

    def _get_manager(self):
        if self._recorder_manager is None:
            from workday.services.recorder import RecordingManager
            self._recorder_manager = RecordingManager(self.db)
        return self._recorder_manager

    def _toggle(self):
        mgr = self._get_manager()
        if mgr.recorder.is_recording:
            mgr.stop()
        else:
            self._recording_thread = threading.Thread(target=mgr.start, daemon=True)
            self._recording_thread.start()
        self._update_ui()

    def _update_ui(self):
        mgr = self._get_manager()
        is_rec = mgr.recorder.is_recording
        color = "#22c55e" if is_rec else "#6b7280"
        self._canvas.itemconfig(self._dot, fill=color)
        self._btn.configure(text="停止录制" if is_rec else "开始录制",
                             fg_color="#ef4444" if is_rec else ["#3B8ED0", "#1F6AA5"])

    def _poll_status(self):
        self._update_ui()
        self.after(3000, self._poll_status)

    def get_is_recording(self) -> bool:
        if self._recorder_manager is None:
            return False
        return self._recorder_manager.recorder.is_recording
