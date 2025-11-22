"""
分析管理模块 - 两阶段 LLM 分析
参考 Dayflow 的 GeminiDirectProvider 实现
"""
import json
import time
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from config_manager import config
from database import Database
from models import Batch, TimelineCard, Observation, ChunkStatus, BatchStatus
from llm_call import transcribe_video, generate_activity_cards
from prompts import get_transcription_prompt, get_activity_cards_prompt
from logger import get_logger

logger = get_logger(__name__)


class AnalysisManager:
    """分析管理器 - 两阶段分析流程"""

    def __init__(self, db: Database):
        self.db = db
        self.is_running = False
        self.analysis_thread: Optional[threading.Thread] = None

        # 分析参数（不再缓存，每次从 config 动态读取以支持运行时配置更新）
        self.check_interval = 60  # 每分钟检查一次

    @property
    def batch_duration(self) -> int:
        """批次时长（秒）- 动态从配置读取"""
        return config.analysis.batch_duration * 60

    @property
    def model(self) -> str:
        """模型名称 - 动态从配置读取"""
        return config.analysis.model

    def start(self):
        """启动分析服务"""
        if self.is_running:
            logger.warning("Analysis service already running")
            return

        self.is_running = True
        logger.info("Starting analysis service...")

        # 启动后台线程
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()

    def stop(self):
        """停止分析服务"""
        if not self.is_running:
            logger.warning("Analysis service not running")
            return

        logger.info("Stopping analysis service...")
        self.is_running = False

        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)

    def _analysis_loop(self):
        """分析循环"""
        while self.is_running:
            try:
                # 处理待分析的录制
                self._process_recordings()

                # 清理旧数据
                self._cleanup_old_data()

            except Exception as e:
                logger.error(f"Error in analysis loop: {e}", exc_info=True)

            # 等待下次检查
            time.sleep(self.check_interval)

    def _process_recordings(self):
        """处理录制数据"""
        # 获取待处理的 chunks
        chunks = self.db.get_pending_chunks()

        if not chunks:
            return

        logger.info(f"Found {len(chunks)} pending chunks to process")

        # 按时间分组为 batches
        batches = self._group_chunks_into_batches(chunks)

        for batch_chunks in batches:
            try:
                self._process_batch(batch_chunks)
            except Exception as e:
                logger.error(f"Error processing batch: {e}", exc_info=True)

    def _group_chunks_into_batches(self, chunks: List) -> List[List]:
        """将 chunks 分组为 batches"""
        if not chunks:
            return []

        batches = []
        current_batch = [chunks[0]]

        for chunk in chunks[1:]:
            # 检查是否在同一批次内
            batch_start_ts = current_batch[0].start_ts
            if chunk.start_ts - batch_start_ts < self.batch_duration:
                current_batch.append(chunk)
            else:
                # 开始新的批次
                batches.append(current_batch)
                current_batch = [chunk]

        # 添加最后一个批次
        if current_batch:
            batches.append(current_batch)

        return batches

    def _process_batch(self, chunks: List):
        """
        处理一个 batch - 两阶段分析流程

        阶段 1: transcribeVideo - 生成 Observations
        阶段 2: generateActivityCards - 生成 TimelineCards
        """
        if not chunks:
            return

        logger.info(f"Processing batch with {len(chunks)} chunks")

        # 创建 batch 记录
        start_ts = chunks[0].start_ts
        end_ts = chunks[-1].end_ts
        day = datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d")

        batch = Batch(
            day=day,
            start_ts=start_ts,
            end_ts=end_ts,
            status=BatchStatus.PROCESSING
        )
        batch_id = self.db.insert_batch(batch)

        try:
            # 标记 chunks 为处理中
            for chunk in chunks:
                self.db.update_chunk_status(chunk.id, ChunkStatus.PROCESSING)

            # 合并视频（如果有多个 chunks）
            if len(chunks) == 1:
                video_path = chunks[0].file_path
            else:
                video_path = self._merge_videos(chunks)

            # ========== 阶段 1: 视频转录 (transcribeVideo) ==========
            logger.info(f"[Stage 1] Transcribing video for batch {batch_id}...")

            duration = end_ts - start_ts
            duration_minutes = int(duration / 60)
            duration_seconds = int(duration % 60)
            duration_string = f"{duration_minutes:02d}:{duration_seconds:02d}"

            prompt1 = get_transcription_prompt(duration_string)

            # 检查是否为调试模式
            if config.analysis.debug_mode:
                logger.info("[Stage 1] DEBUG MODE: Skipping LLM call, using default observations")
                # 生成默认的观察记录
                mid_ts = start_ts + (end_ts - start_ts) // 2
                response1 = json.dumps([
                    {
                        "startTimestamp": "00:00",
                        "endTimestamp": duration_string,
                        "description": f"[调试模式] 默认观察记录 - 批次时间: {datetime.fromtimestamp(start_ts).strftime('%H:%M')} - {datetime.fromtimestamp(end_ts).strftime('%H:%M')}"
                    }
                ])
            else:
                response1 = transcribe_video(video_path, prompt1, self.model)

            # 解析第一阶段结果
            observations_data = self._parse_observations(response1, start_ts)

            if not observations_data:
                logger.warning(f"[Stage 1] Failed: No observations generated for batch {batch_id}")
                self.db.update_batch_status(batch_id, BatchStatus.FAILED)
                for chunk in chunks:
                    self.db.update_chunk_status(chunk.id, ChunkStatus.FAILED)
                return

            # 保存 observations 到数据库
            observations = []
            for obs_data in observations_data:
                obs = Observation(
                    batch_id=batch_id,
                    start_ts=obs_data['start_ts'],
                    end_ts=obs_data['end_ts'],
                    observation=obs_data['description']
                )
                observations.append(obs)

            self.db.insert_observations(observations)
            logger.info(f"[Stage 1] Success: Generated {len(observations)} observations")

            # ========== 阶段 2: 生成活动卡片 (generateActivityCards) ==========
            logger.info(f"[Stage 2] Generating activity cards for batch {batch_id}...")

            # 格式化 observations 为文本
            observations_text = self._format_observations(observations)

            # TODO: 实现滑动窗口逻辑获取已存在的卡片
            existing_cards_json = "[]"

            prompt2 = get_activity_cards_prompt(observations_text, existing_cards_json)

            # 检查是否为调试模式
            if config.analysis.debug_mode:
                logger.info("[Stage 2] DEBUG MODE: Skipping LLM call, using default activity card")
                # 生成默认的活动卡片
                start_time_str = datetime.fromtimestamp(start_ts).strftime("%I:%M %p").lstrip('0')
                end_time_str = datetime.fromtimestamp(end_ts).strftime("%I:%M %p").lstrip('0')
                response2 = json.dumps([
                    {
                        "startTime": start_time_str,
                        "endTime": end_time_str,
                        "category": "其他",
                        "subcategory": "调试",
                        "title": "[调试模式] 默认活动",
                        "summary": "调试模式下生成的默认活动卡片",
                        "detailedSummary": f"这是调试模式下自动生成的默认活动卡片，用于测试流程而不消耗 Token。时间范围：{start_time_str} - {end_time_str}"
                    }
                ])
            else:
                response2 = generate_activity_cards(prompt2, self.model)

            # 解析第二阶段结果（传递 batch 的 start_ts 用于正确解析日期）
            cards_data = self._parse_activity_cards(response2, start_ts)

            if not cards_data:
                logger.warning(f"[Stage 2] Failed: No cards generated for batch {batch_id}")
                self.db.update_batch_status(batch_id, BatchStatus.FAILED)
                for chunk in chunks:
                    self.db.update_chunk_status(chunk.id, ChunkStatus.FAILED)
                return

            # 保存时间线卡片
            for card_data in cards_data:
                # 确保 Card 时间在 batch 时间范围内
                card_start = max(card_data['start_ts'], start_ts)
                card_end = min(card_data['end_ts'], end_ts)

                # 如果时间范围无效（结束时间早于开始时间），使用 batch 的时间范围
                if card_end <= card_start:
                    logger.warning(f"Invalid card time range, using batch time range")
                    card_start = start_ts
                    card_end = end_ts

                card = TimelineCard(
                    batch_id=batch_id,
                    title=card_data.get('title', 'Unknown Activity'),
                    description=card_data.get('detailedSummary', card_data.get('summary', '')),
                    start_ts=card_start,
                    end_ts=card_end,
                    category=card_data.get('category', 'other'),
                    video_path=video_path
                )
                self.db.insert_timeline_card(card)

            # 更新状态
            self.db.update_batch_status(batch_id, BatchStatus.COMPLETED)
            for chunk in chunks:
                self.db.update_chunk_status(chunk.id, ChunkStatus.COMPLETED)

            logger.info(f"[Stage 2] Success: Generated {len(cards_data)} cards for batch {batch_id}")

        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {e}", exc_info=True)

            self.db.update_batch_status(batch_id, BatchStatus.FAILED)
            for chunk in chunks:
                self.db.update_chunk_status(chunk.id, ChunkStatus.FAILED)

    def _parse_observations(self, response: str, batch_start_ts: int) -> List[Dict[str, Any]]:
        """
        解析视频转录结果

        Expected format:
        [
          {
            "startTimestamp": "MM:SS",
            "endTimestamp": "MM:SS",
            "description": "..."
          }
        ]
        """
        try:
            data = json.loads(response)

            if not isinstance(data, list):
                logger.error(f"Invalid response format in observations: expected list, got {type(data)}")
                return []

            observations = []
            for item in data:
                start_seconds = self._parse_timestamp(item['startTimestamp'])
                end_seconds = self._parse_timestamp(item['endTimestamp'])

                obs = {
                    'start_ts': batch_start_ts + start_seconds,
                    'end_ts': batch_start_ts + end_seconds,
                    'description': item['description']
                }
                observations.append(obs)

            return observations

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse observations JSON: {e}")
            logger.debug(f"Response: {response[:500]}")
            return []
        except KeyError as e:
            logger.error(f"Missing required field in observation: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing observations: {e}", exc_info=True)
            return []

    def _parse_activity_cards(self, response: str, batch_start_ts: int) -> List[Dict[str, Any]]:
        """
        解析活动卡片结果

        Args:
            response: LLM 返回的 JSON 字符串
            batch_start_ts: batch 的开始时间戳（用于确定日期）

        Expected format:
        [
          {
            "startTime": "1:12 PM",
            "endTime": "1:30 PM",
            "category": "工作",
            "subcategory": "编程",
            "title": "...",
            "summary": "...",
            "detailedSummary": "..."
          }
        ]
        """
        try:
            data = json.loads(response)

            if not isinstance(data, list):
                logger.error(f"Invalid response format in activity cards: expected list, got {type(data)}")
                return []

            # 获取 batch 的日期
            batch_date = datetime.fromtimestamp(batch_start_ts).date()

            cards = []
            for item in data:
                # 解析时间（格式：1:12 PM），使用 batch 的日期
                start_ts = self._parse_time_string(item['startTime'], batch_date)
                end_ts = self._parse_time_string(item['endTime'], batch_date)

                card = {
                    'start_ts': start_ts,
                    'end_ts': end_ts,
                    'category': item.get('category', '其他'),
                    'subcategory': item.get('subcategory', ''),
                    'title': item.get('title', 'Unknown'),
                    'summary': item.get('summary', ''),
                    'detailedSummary': item.get('detailedSummary', ''),
                    'distractions': item.get('distractions', [])
                }
                cards.append(card)

            return cards

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse activity cards JSON: {e}")
            logger.debug(f"Response: {response[:500]}")
            return []
        except KeyError as e:
            logger.error(f"Missing required field in card: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing activity cards: {e}", exc_info=True)
            return []

    def _parse_timestamp(self, timestamp: str) -> int:
        """解析时间戳 MM:SS -> 秒数"""
        parts = timestamp.split(':')
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        return 0

    def _parse_time_string(self, time_str: str, base_date=None) -> int:
        """
        解析时间字符串 '1:12 PM' -> Unix timestamp

        Args:
            time_str: 时间字符串（如 "1:12 PM"）
            base_date: 基准日期（date 对象），如果为 None 则使用今天
        """
        try:
            dt = datetime.strptime(time_str, "%I:%M %p")

            # 使用提供的日期或今天的日期
            if base_date is None:
                base_date = datetime.now().date()

            result = datetime.combine(base_date, dt.time())
            return int(result.timestamp())
        except Exception as e:
            logger.error(f"Error parsing time string '{time_str}': {e}")
            return int(datetime.now().timestamp())

    def _format_observations(self, observations: List[Observation]) -> str:
        """格式化 observations 为文本"""
        lines = []
        for obs in observations:
            start_time = self._format_timestamp(obs.start_ts)
            end_time = self._format_timestamp(obs.end_ts)
            lines.append(f"[{start_time} - {end_time}]: {obs.observation}")
        return "\n".join(lines)

    def _format_timestamp(self, ts: int) -> str:
        """格式化时间戳为 'h:mm AM/PM' 格式"""
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%I:%M %p").lstrip('0')

    def _merge_videos(self, chunks: List) -> str:
        """合并多个视频文件"""
        import cv2

        if not chunks:
            raise ValueError("No chunks to merge")

        # 生成输出文件名
        start_ts = chunks[0].start_ts
        timestamp = datetime.fromtimestamp(start_ts).strftime("%Y%m%d_%H%M%S")
        output_path = Path(config.recording.output_dir) / f"batch_{timestamp}.mp4"

        # 读取第一个视频以获取参数
        first_video = cv2.VideoCapture(chunks[0].file_path)
        fps = first_video.get(cv2.CAP_PROP_FPS)
        width = int(first_video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(first_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        first_video.release()

        # 创建输出视频 - 优先使用 H.264 编码（浏览器兼容）
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        # 如果 avc1 不可用，尝试 H264
        if not out.isOpened():
            logger.warning("avc1 codec not available, trying H264...")
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        # 最后回退到 mp4v（可能浏览器不兼容）
        if not out.isOpened():
            logger.warning("H264 codec not available, falling back to mp4v (may not play in browser)")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not out.isOpened():
            raise RuntimeError(f"Failed to create video writer for {output_path}")

        try:
            # 合并所有视频
            for chunk in chunks:
                video = cv2.VideoCapture(chunk.file_path)

                while True:
                    ret, frame = video.read()
                    if not ret:
                        break
                    out.write(frame)

                video.release()

        finally:
            out.release()

        logger.info(f"Merged {len(chunks)} videos into {output_path}")
        return str(output_path)

    def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            retention_days = config.retention.days
            self.db.delete_old_chunks(retention_days)

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}", exc_info=True)

    def trigger_analysis_now(self):
        """立即触发分析"""
        logger.info("Triggering immediate analysis...")
        try:
            self._process_recordings()
        except Exception as e:
            logger.error(f"Error in triggered analysis: {e}", exc_info=True)

    def reprocess_day(self, day: str) -> dict:
        """重新处理指定日期的数据"""
        try:
            logger.info(f"Reprocessing day: {day}")

            # 删除该天的时间线卡片
            video_paths = self.db.delete_timeline_cards_by_day(day)

            # 删除视频文件
            for path in video_paths:
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception as e:
                    logger.error(f"Error deleting video {path}: {e}")

            # 获取该天的批次并重置状态
            batches = self.db.get_batches_by_day(day)
            for batch in batches:
                self.db.update_batch_status(batch.id, BatchStatus.PENDING)

            # 触发分析
            self.trigger_analysis_now()

            return {
                "success": True,
                "message": f"Reprocessing {len(batches)} batches for {day}"
            }

        except Exception as e:
            logger.error(f"Error reprocessing day {day}: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e)
            }
