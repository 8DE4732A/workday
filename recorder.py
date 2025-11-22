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
import io
import cv2
import numpy as np

from config_manager import config
from database import Database
from models import RecordingChunk, ChunkStatus
from logger import get_logger

logger = get_logger(__name__)


class ScreenRecorder:
    """屏幕录制器"""

    def __init__(self, db: Database):
        self.db = db
        self.is_recording = False
        self.output_dir = Path(config.recording.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 录制参数
        self.capture_interval = config.recording.capture_interval
        self.chunk_duration = config.recording.chunk_duration
        self.quality = config.recording.quality
        self.format = config.recording.format
        self.monitor_index = config.recording.monitor_index

        # 当前录制状态
        self.current_chunk_id: Optional[int] = None
        self.current_chunk_frames: List[np.ndarray] = []
        self.chunk_start_time: Optional[float] = None

    @staticmethod
    def list_monitors() -> List[dict]:
        """
        列出所有可用的显示器信息

        Returns:
            显示器信息列表，每个元素包含索引、宽度、高度等信息
        """
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

        try:
            with mss.mss() as sct:
                # 获取所有显示器信息
                monitors = sct.monitors
                logger.info(f"Available monitors: {len(monitors) - 1}")  # -1 因为索引0是所有显示器

                # 验证显示器索引
                if self.monitor_index < 0 or self.monitor_index >= len(monitors):
                    logger.error(f"Invalid monitor index {self.monitor_index}, falling back to all monitors (0)")
                    self.monitor_index = 0

                # 选择要录制的显示器
                monitor = monitors[self.monitor_index]

                if self.monitor_index == 0:
                    logger.info(f"Screen recording started - Capturing ALL monitors ({monitor['width']}x{monitor['height']})")
                else:
                    logger.info(f"Screen recording started - Monitor {self.monitor_index} ({monitor['width']}x{monitor['height']})")

                while self.is_recording:
                    loop_start = time.time()

                    # 初始化新的 chunk
                    if self.chunk_start_time is None:
                        self.chunk_start_time = time.time()
                        self.current_chunk_frames = []

                    # 截图
                    sct_img = sct.grab(monitor)

                    # 转换为 numpy 数组
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    frame = np.array(img)

                    # 添加到当前 chunk
                    self.current_chunk_frames.append(frame)

                    # 检查是否需要保存 chunk
                    elapsed = time.time() - self.chunk_start_time
                    if elapsed >= self.chunk_duration:
                        self._save_chunk()

                    # 控制帧率
                    elapsed = time.time() - loop_start
                    sleep_time = max(0, self.capture_interval - elapsed)
                    time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Recording error: {e}", exc_info=True)
        finally:
            # 保存最后一个 chunk
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

    def _save_chunk(self):
        """保存当前 chunk"""
        if not self.current_chunk_frames:
            return

        try:
            start_ts = int(self.chunk_start_time)
            end_ts = int(time.time())

            # 生成文件名
            timestamp = datetime.fromtimestamp(start_ts).strftime("%Y%m%d_%H%M%S")
            video_filename = f"chunk_{timestamp}.mp4"
            video_path = self.output_dir / video_filename

            # 保存为视频文件
            self._save_video(self.current_chunk_frames, str(video_path))

            # 保存到数据库
            chunk = RecordingChunk(
                start_ts=start_ts,
                end_ts=end_ts,
                file_path=str(video_path),
                status=ChunkStatus.PENDING
            )
            chunk_id = self.db.insert_chunk(chunk)

            logger.info(f"Saved chunk {chunk_id}: {video_path} ({len(self.current_chunk_frames)} frames)")

            # 重置状态
            self.current_chunk_frames = []
            self.chunk_start_time = None

        except Exception as e:
            logger.error(f"Error saving chunk: {e}", exc_info=True)

    def _save_video(self, frames: List[np.ndarray], output_path: str):
        """
        将帧列表保存为 MP4 视频

        Args:
            frames: 帧列表
            output_path: 输出路径
        """
        if not frames:
            return

        # 获取视频尺寸
        height, width = frames[0].shape[:2]

        # 创建视频写入器，使用 H.264 编码（浏览器原生支持）
        # 优先尝试 avc1 (H.264)，如果失败则回退到 mp4v
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        fps = 1.0 / self.capture_interval  # 根据截图间隔计算 FPS
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 如果 avc1 失败，尝试使用 H264
        if not out.isOpened():
            logger.warning("Failed to use 'avc1' codec, trying 'H264'")
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 如果 H264 也失败，回退到 mp4v（兼容性最好但浏览器支持差）
        if not out.isOpened():
            logger.warning("Failed to use 'H264' codec, falling back to 'mp4v'")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 检查视频写入器是否成功打开
        if not out.isOpened():
            raise RuntimeError(f"Failed to create video writer for {output_path}")

        # 记录使用的编码格式
        codec_name = {
            cv2.VideoWriter_fourcc(*'avc1'): 'H.264 (avc1)',
            cv2.VideoWriter_fourcc(*'H264'): 'H.264 (H264)',
            cv2.VideoWriter_fourcc(*'mp4v'): 'MPEG-4 Part 2 (mp4v)'
        }.get(fourcc, f'Unknown ({fourcc})')
        logger.info(f"Creating video with codec: {codec_name}, FPS: {fps}, Size: {width}x{height}")

        try:
            for frame in frames:
                # OpenCV 使用 BGR 格式
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                out.write(bgr_frame)
        finally:
            out.release()
            logger.info(f"Video saved: {output_path}")

    def _save_image(self, frame: np.ndarray, output_path: str):
        """
        保存单张图片（备用方法）

        Args:
            frame: 图片帧
            output_path: 输出路径
        """
        img = Image.fromarray(frame)

        if self.format.lower() == 'jpg':
            img.save(output_path, 'JPEG', quality=self.quality)
        else:
            img.save(output_path, self.format.upper())


class RecordingManager:
    """录制管理器 - 后台服务"""

    def __init__(self, db: Database):
        self.db = db
        self.recorder = ScreenRecorder(db)
        self.is_running = False

    def start(self):
        """启动录制服务"""
        if self.is_running:
            logger.warning("Recording service already running")
            return

        self.is_running = True
        logger.info("Starting recording service...")

        # 启动录制
        self.recorder.start_recording()

    def stop(self):
        """停止录制服务"""
        if not self.is_running:
            logger.warning("Recording service not running")
            return

        logger.info("Stopping recording service...")
        self.recorder.stop_recording()
        self.is_running = False

    def get_status(self) -> dict:
        """获取录制状态"""
        return {
            "is_recording": self.recorder.is_recording,
            "output_dir": str(self.recorder.output_dir),
            "chunk_duration": self.recorder.chunk_duration,
            "capture_interval": self.recorder.capture_interval
        }
