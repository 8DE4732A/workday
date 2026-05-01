"""
屏幕录制模块
使用 mss 进行跨平台截图，支持生成视频用于 AI 分析
"""
import time
import mss
import mss.tools
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from PIL import Image
import cv2
import numpy as np

from workday.core.config import get_config
from workday.core.database import Database
from workday.core.models import RecordingChunk, ChunkStatus
from workday.core.logger import get_logger

logger = get_logger(__name__)


class ScreenRecorder:
    """屏幕录制器"""

    def __init__(self, db: Database):
        self.db = db
        self.is_recording = False
        cfg = get_config()
        self.output_dir = Path(cfg.recording.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.capture_interval = cfg.recording.capture_interval
        self.chunk_duration = cfg.recording.chunk_duration
        self.quality = cfg.recording.quality
        self.format = cfg.recording.format
        self.monitor_index = cfg.recording.monitor_index
        self.static_diff_threshold = cfg.recording.static_diff_threshold
        self.static_frame_ratio = cfg.recording.static_frame_ratio

        self.current_chunk_id: Optional[int] = None
        self.current_chunk_frames: List[np.ndarray] = []
        self.chunk_start_time: Optional[float] = None
        self._prev_small_gray: Optional[np.ndarray] = None
        self._static_flags: List[bool] = []

    @staticmethod
    def list_monitors() -> List[dict]:
        """列出所有可用的显示器信息"""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                monitor_info = []
                for idx, monitor in enumerate(monitors):
                    info = {
                        "index": idx,
                        "width": monitor.get("width", 0),
                        "height": monitor.get("height", 0),
                        "left": monitor.get("left", 0),
                        "top": monitor.get("top", 0),
                    }
                    if idx == 0:
                        info["description"] = "All monitors combined"
                    elif idx == 1:
                        info["description"] = "Primary monitor"
                    else:
                        info["description"] = f"Monitor {idx}"
                    monitor_info.append(info)
                return monitor_info
        except Exception as e:
            logger.error(f"Error listing monitors: {e}", exc_info=True)
            return []

    def start_recording(self):
        """开始录制"""
        if self.is_recording:
            logger.warning("Already recording")
            return

        self.is_recording = True
        self._prev_small_gray = None
        self._static_flags = []

        try:
            with mss.mss() as sct:
                monitors = sct.monitors
                logger.debug(f"Available monitors: {len(monitors) - 1}")

                if self.monitor_index < 0 or self.monitor_index >= len(monitors):
                    logger.error(f"Invalid monitor index {self.monitor_index}, falling back to all monitors (0)")
                    self.monitor_index = 0

                monitor = monitors[self.monitor_index]

                if self.monitor_index == 0:
                    logger.info(f"Screen recording started - ALL monitors ({monitor['width']}x{monitor['height']})")
                else:
                    logger.info(f"Screen recording started - Monitor {self.monitor_index} ({monitor['width']}x{monitor['height']})")

                while self.is_recording:
                    loop_start = time.time()

                    if self.chunk_start_time is None:
                        self.chunk_start_time = time.time()
                        self.current_chunk_frames = []

                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    frame = np.array(img)
                    self._static_flags.append(self._is_static_frame(frame))
                    self.current_chunk_frames.append(frame)

                    elapsed = time.time() - self.chunk_start_time
                    if elapsed >= self.chunk_duration:
                        self._save_chunk()

                    elapsed = time.time() - loop_start
                    sleep_time = max(0, self.capture_interval - elapsed)
                    time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Recording error: {e}", exc_info=True)
        finally:
            if self.current_chunk_frames:
                self._save_chunk()
            self.is_recording = False

    def stop_recording(self):
        """停止录制"""
        if not self.is_recording:
            logger.warning("Not recording")
            return
        logger.info("Stopping screen recording...")
        self.is_recording = False

    def _is_static_frame(self, frame: np.ndarray) -> bool:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        small = cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA)
        if self._prev_small_gray is None:
            self._prev_small_gray = small
            return False
        diff = float(np.mean(np.abs(small.astype(np.int16) - self._prev_small_gray.astype(np.int16))))
        self._prev_small_gray = small
        return diff < self.static_diff_threshold

    def _save_chunk(self):
        if not self.current_chunk_frames or self.chunk_start_time is None:
            return

        try:
            start_ts = int(self.chunk_start_time)
            end_ts = int(time.time())

            static_flags = self._static_flags or []
            if static_flags:
                static_ratio = sum(static_flags) / len(static_flags)
            else:
                static_ratio = 0.0

            if static_ratio >= self.static_frame_ratio:
                chunk = RecordingChunk(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    file_path="",
                    status=ChunkStatus.SKIPPED
                )
                chunk_id = self.db.insert_chunk(chunk)
                static_count = sum(static_flags)
                total_count = len(static_flags)
                logger.debug(
                    f"Chunk skipped (static screen: {static_count}/{total_count} frames, "
                    f"ratio={static_ratio:.2f})"
                )
            else:
                timestamp = datetime.fromtimestamp(start_ts).strftime("%Y%m%d_%H%M%S")
                video_filename = f"chunk_{timestamp}.mp4"
                video_path = self.output_dir / video_filename

                self._save_video(self.current_chunk_frames, str(video_path))

                chunk = RecordingChunk(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    file_path=str(video_path),
                    status=ChunkStatus.PENDING
                )
                chunk_id = self.db.insert_chunk(chunk)
                logger.debug(f"Saved chunk {chunk_id}: {video_path} ({len(self.current_chunk_frames)} frames)")

            self.current_chunk_frames = []
            self.chunk_start_time = None
            self._static_flags = []

        except Exception as e:
            logger.error(f"Error saving chunk: {e}", exc_info=True)

    def _save_video(self, frames: List[np.ndarray], output_path: str):
        if not frames:
            return

        height, width = frames[0].shape[:2]
        fps = 1.0 / self.capture_interval

        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            logger.warning("Failed to use 'avc1' codec, trying 'H264'")
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            logger.warning("Failed to use 'H264' codec, falling back to 'mp4v'")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            raise RuntimeError(f"Failed to create video writer for {output_path}")

        try:
            for frame in frames:
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                out.write(bgr_frame)
        finally:
            out.release()
            logger.debug(f"Video saved: {output_path}")


class RecordingManager:
    """录制管理器 - 后台服务"""

    def __init__(self, db: Database):
        self.db = db
        self.recorder = ScreenRecorder(db)
        self.is_running = False

    def start(self):
        if self.is_running:
            logger.warning("Recording service already running")
            return
        self.is_running = True
        logger.info("Starting recording service...")
        self.recorder.start_recording()

    def stop(self):
        if not self.is_running:
            logger.warning("Recording service not running")
            return
        logger.info("Stopping recording service...")
        self.recorder.stop_recording()
        self.is_running = False

    def get_status(self) -> dict:
        return {
            "is_recording": self.recorder.is_recording,
            "output_dir": str(self.recorder.output_dir),
            "chunk_duration": self.recorder.chunk_duration,
            "capture_interval": self.recorder.capture_interval
        }
