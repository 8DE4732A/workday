"""
分析管理模块 - 两阶段 LLM 分析
参考 Dayflow 的 GeminiDirectProvider 实现
"""
import json
import time
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from workday.core.config import get_config
from workday.core.database import Database
from workday.core.models import Batch, TimelineCard, Observation, ChunkStatus, BatchStatus
from workday.services.llm_call import transcribe_video, generate_activity_cards, chat_with_images
from workday.services.prompts import get_transcription_prompt, get_activity_cards_prompt, get_transcription_prompt_images
from workday.core.logger import get_logger

logger = get_logger(__name__)


class AnalysisManager:
    """分析管理器 - 两阶段分析流程"""

    def __init__(self, db: Database):
        self.db = db
        self.is_running = False
        self.analysis_thread: Optional[threading.Thread] = None
        self.check_interval = 60

    @property
    def batch_duration(self) -> int:
        return get_config().analysis.batch_duration * 60

    @property
    def model(self) -> str:
        return get_config().llm.model

    def start(self):
        if self.is_running:
            logger.warning("Analysis service already running")
            return
        self.is_running = True
        logger.info("Starting analysis service...")
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()

    def stop(self):
        if not self.is_running:
            logger.warning("Analysis service not running")
            return
        logger.info("Stopping analysis service...")
        self.is_running = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)

    def _analysis_loop(self):
        while self.is_running:
            try:
                self._run_stage1()
                self._run_stage2()
                self._cleanup_old_data()
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}", exc_info=True)
            time.sleep(self.check_interval)

    # ================================================================
    # Stage 1：视频转录 → Observations，每批 chunk 独立处理
    # ================================================================

    def _run_stage1(self):
        chunks = self.db.get_pending_chunks()
        if not chunks:
            return

        logger.info(f"[Stage 1] Found {len(chunks)} pending chunks")
        for batch_chunks in self._group_chunks_into_batches(chunks):
            try:
                self._transcribe_batch(batch_chunks)
            except Exception as e:
                logger.error(f"[Stage 1] Error processing batch: {e}", exc_info=True)

    def _group_chunks_into_batches(self, chunks: List) -> List[List]:
        if not chunks:
            return []

        mode = get_config().get('analysis.recognition_mode', 'video')
        if mode == 'image':
            target_count = get_config().analysis.batch_duration
            chunk_duration = get_config().recording.chunk_duration
            chunks_per_batch = max(1, target_count // max(1, chunk_duration))
            return [chunks[i:i + chunks_per_batch] for i in range(0, len(chunks), chunks_per_batch)]

        batches = []
        current_batch = [chunks[0]]

        for chunk in chunks[1:]:
            batch_start_ts = current_batch[0].start_ts
            if chunk.start_ts - batch_start_ts < self.batch_duration:
                current_batch.append(chunk)
            else:
                batches.append(current_batch)
                current_batch = [chunk]

        if current_batch:
            batches.append(current_batch)

        return batches

    def _transcribe_batch(self, chunks: List):
        """Stage 1：将一批 chunks 转录为 Observations，完成后标记 batch 为 TRANSCRIBED"""
        if not chunks:
            return

        start_ts = chunks[0].start_ts
        end_ts = chunks[-1].end_ts
        day = datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d")

        batch = Batch(day=day, start_ts=start_ts, end_ts=end_ts, status=BatchStatus.PROCESSING)
        batch_id = self.db.insert_batch(batch)

        try:
            for chunk in chunks:
                self.db.update_chunk_status(chunk.id, ChunkStatus.PROCESSING)

            # スキップされたチャンクを除外してビデオパスを取得
            video_chunks = [c for c in chunks if c.file_path]
            if not video_chunks:
                logger.info(f"[Stage 1] Batch {batch_id}: all chunks skipped, marking TRANSCRIBED with no observations")
                self.db.update_batch_status(batch_id, BatchStatus.TRANSCRIBED)
                for chunk in chunks:
                    self.db.update_chunk_status(chunk.id, ChunkStatus.COMPLETED)
                return

            recognition_mode = get_config().get('analysis.recognition_mode', 'video')

            if len(video_chunks) == 1:
                video_path = video_chunks[0].file_path
            elif recognition_mode != 'image':
                video_path = self._merge_videos(video_chunks)
            else:
                video_path = video_chunks[0].file_path  # 图片模式不需要合并视频

            duration = end_ts - start_ts
            duration_string = f"{int(duration / 60):02d}:{int(duration % 60):02d}"
            prompt1 = get_transcription_prompt(duration_string)

            if get_config().analysis.debug_mode:
                logger.info(f"[Stage 1] Batch {batch_id}: DEBUG MODE")
                response1 = json.dumps([{
                    "startTimestamp": "00:00",
                    "endTimestamp": duration_string,
                    "description": f"[调试模式] 默认观察记录 - {datetime.fromtimestamp(start_ts).strftime('%H:%M')} - {datetime.fromtimestamp(end_ts).strftime('%H:%M')}"
                }])
            else:
                if recognition_mode == 'image':
                    response1 = self._transcribe_batch_images(batch_id, video_chunks, start_ts, duration_string)
                    if response1 is None:
                        return
                else:
                    logger.info(f"[Stage 1] Transcribing batch {batch_id} ({duration_string})...")
                    response1 = transcribe_video(video_path, prompt1, self.model)

            observations_data = self._parse_observations(response1, start_ts)

            if not observations_data:
                logger.warning(f"[Stage 1] Batch {batch_id}: no observations parsed, marking FAILED")
                self.db.update_batch_status(batch_id, BatchStatus.FAILED)
                for chunk in chunks:
                    self.db.update_chunk_status(chunk.id, ChunkStatus.FAILED)
                return

            observations = [
                Observation(batch_id=batch_id, start_ts=d['start_ts'],
                            end_ts=d['end_ts'], observation=d['description'])
                for d in observations_data
            ]
            self.db.insert_observations(observations)

            self.db.update_batch_status(batch_id, BatchStatus.TRANSCRIBED)
            for chunk in chunks:
                self.db.update_chunk_status(chunk.id, ChunkStatus.COMPLETED)

            logger.info(f"[Stage 1] Batch {batch_id}: {len(observations)} observations, status=TRANSCRIBED")

        except Exception as e:
            logger.error(f"[Stage 1] Batch {batch_id} failed: {e}", exc_info=True)
            self.db.update_batch_status(batch_id, BatchStatus.FAILED)
            for chunk in chunks:
                self.db.update_chunk_status(chunk.id, ChunkStatus.FAILED)

    # ================================================================
    # Stage 2：聚合 Observations → Timeline Cards
    # 触发条件（OR）：
    #   A. 最早 TRANSCRIBED batch 的 start_ts 距今 >= card_window_minutes
    #   B. 待处理 observations 总数 >= card_min_observations
    # ================================================================

    def _run_stage2(self):
        transcribed = self.db.get_transcribed_batches()
        if not transcribed:
            return

        cfg = get_config().analysis
        card_window_seconds = cfg.card_window_minutes * 60
        card_min_obs = cfg.card_min_observations

        now = int(time.time())
        earliest_start = transcribed[0].start_ts
        elapsed = now - earliest_start

        batch_ids = [b.id for b in transcribed if b.id is not None]
        obs_count = self.db.count_observations_for_batches(batch_ids)

        time_triggered = elapsed >= card_window_seconds
        count_triggered = obs_count >= card_min_obs

        if not (time_triggered or count_triggered):
            logger.debug(
                f"[Stage 2] Not triggered: elapsed={elapsed}s/{card_window_seconds}s, "
                f"obs={obs_count}/{card_min_obs}"
            )
            return

        trigger_reason = []
        if time_triggered:
            trigger_reason.append(f"time ({elapsed}s >= {card_window_seconds}s)")
        if count_triggered:
            trigger_reason.append(f"count ({obs_count} >= {card_min_obs})")
        logger.info(f"[Stage 2] Triggered by: {', '.join(trigger_reason)}")

        self._generate_cards_for_batches(transcribed)

    def _generate_cards_for_batches(self, batches: List):
        """Stage 2：将一批 TRANSCRIBED batches 的所有 observations 合并生成 Timeline Cards"""
        if not batches:
            return

        batch_ids = [b.id for b in batches]
        start_ts = batches[0].start_ts
        end_ts = batches[-1].end_ts

        # 标记所有参与的 batch 为 PROCESSING
        for batch in batches:
            self.db.update_batch_status(batch.id, BatchStatus.PROCESSING)

        try:
            observations = []
            for batch in batches:
                observations.extend(self.db.get_observations_by_batch(batch.id))
            observations.sort(key=lambda o: o.start_ts)

            if not observations:
                logger.warning(f"[Stage 2] No observations found for batches {batch_ids}, marking COMPLETED")
                for batch in batches:
                    self.db.update_batch_status(batch.id, BatchStatus.COMPLETED)
                return

            observations_text = self._format_observations(observations)
            existing_cards_json = self._fetch_context_cards_json(start_ts)
            prompt2 = get_activity_cards_prompt(observations_text, existing_cards_json)

            if get_config().analysis.debug_mode:
                logger.info("[Stage 2] DEBUG MODE")
                start_time_str = datetime.fromtimestamp(start_ts).strftime("%I:%M %p").lstrip('0')
                end_time_str = datetime.fromtimestamp(end_ts).strftime("%I:%M %p").lstrip('0')
                response2 = json.dumps([{
                    "startTime": start_time_str,
                    "endTime": end_time_str,
                    "category": "其他",
                    "subcategory": "调试",
                    "title": "[调试模式] 默认活动",
                    "summary": "调试模式下生成的默认活动卡片",
                    "detailedSummary": f"调试模式，时间范围：{start_time_str} - {end_time_str}"
                }])
            else:
                logger.info(f"[Stage 2] Generating cards for {len(observations)} observations "
                            f"across {len(batches)} batches...")
                response2 = generate_activity_cards(prompt2, self.model)

            cards_data = self._parse_activity_cards(response2, start_ts)

            if not cards_data:
                logger.warning(f"[Stage 2] No cards parsed, marking batches FAILED")
                for batch in batches:
                    self.db.update_batch_status(batch.id, BatchStatus.FAILED)
                return

            # 卡片归属到时间范围最近的 batch
            for card_data in cards_data:
                card_start = card_data['start_ts']
                card_end = card_data['end_ts']

                owning_batch = batches[0]
                for batch in batches:
                    if batch.start_ts <= card_start:
                        owning_batch = batch

                card_start = max(card_start, start_ts)
                card_end = min(card_end, end_ts)
                if card_end <= card_start:
                    card_start = start_ts
                    card_end = end_ts

                # 找对应批次最近的视频路径
                video_path = self._find_video_for_batch(owning_batch)

                card = TimelineCard(
                    batch_id=owning_batch.id,
                    title=card_data.get('title', 'Unknown Activity'),
                    description=card_data.get('detailedSummary', card_data.get('summary', '')),
                    start_ts=card_start,
                    end_ts=card_end,
                    category=card_data.get('category', '其他'),
                    video_path=video_path,
                )
                self.db.insert_timeline_card(card)

            for batch in batches:
                self.db.update_batch_status(batch.id, BatchStatus.COMPLETED)

            logger.info(f"[Stage 2] Generated {len(cards_data)} cards, batches marked COMPLETED")

        except Exception as e:
            logger.error(f"[Stage 2] Failed: {e}", exc_info=True)
            for batch in batches:
                self.db.update_batch_status(batch.id, BatchStatus.FAILED)

    def _find_video_for_batch(self, batch) -> Optional[str]:
        """返回该 batch 时间范围内第一个有效视频路径（用于卡片关联）"""
        try:
            chunks = self.db.get_chunks_by_time_range(batch.start_ts, batch.end_ts)
            for chunk in chunks:
                if chunk.file_path:
                    return chunk.file_path
        except Exception:
            pass
        return None

    def _fetch_context_cards_json(self, before_ts: int) -> str:
        """查询 before_ts 之前的前序活动卡片，序列化为 JSON 字符串供 Stage 2 prompt 使用"""
        try:
            cfg = get_config().analysis
            since_ts = before_ts - cfg.context_window_minutes * 60
            cards = self.db.get_preceding_timeline_cards(
                before_ts=before_ts,
                since_ts=since_ts,
                limit=cfg.context_max_cards,
            )
            if not cards:
                return "[]"
            result = []
            for card in cards:
                result.append({
                    "startTime": self._format_timestamp(card.start_ts),
                    "endTime": self._format_timestamp(card.end_ts),
                    "category": card.category,
                    "title": card.title,
                    "summary": card.description,
                })
            logger.info(f"[Stage 2] Loaded {len(result)} preceding cards as context")
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[Stage 2] Failed to fetch context cards: {e}")
            return "[]"

    def _parse_observations(self, response: str, batch_start_ts: int) -> List[Dict[str, Any]]:
        try:
            data = json.loads(response)
            if not isinstance(data, list):
                logger.error(f"Invalid response format in observations: expected list, got {type(data)}")
                return []

            observations = []
            for item in data:
                start_seconds = self._parse_timestamp(item['startTimestamp'])
                end_seconds = self._parse_timestamp(item['endTimestamp'])
                observations.append({
                    'start_ts': batch_start_ts + start_seconds,
                    'end_ts': batch_start_ts + end_seconds,
                    'description': item['description']
                })
            return observations

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse observations JSON: {e}")
            return []
        except KeyError as e:
            logger.error(f"Missing required field in observation: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing observations: {e}", exc_info=True)
            return []

    def _parse_activity_cards(self, response: str, batch_start_ts: int) -> List[Dict[str, Any]]:
        try:
            data = json.loads(response)
            if not isinstance(data, list):
                logger.error(f"Invalid response format in activity cards: expected list, got {type(data)}")
                return []

            batch_date = datetime.fromtimestamp(batch_start_ts).date()
            cards = []
            for item in data:
                start_ts = self._parse_time_string(item['startTime'], batch_date)
                end_ts = self._parse_time_string(item['endTime'], batch_date)
                cards.append({
                    'start_ts': start_ts,
                    'end_ts': end_ts,
                    'category': item.get('category', '其他'),
                    'subcategory': item.get('subcategory', ''),
                    'title': item.get('title', 'Unknown'),
                    'summary': item.get('summary', ''),
                    'detailedSummary': item.get('detailedSummary', ''),
                    'distractions': item.get('distractions', [])
                })
            return cards

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse activity cards JSON: {e}")
            return []
        except KeyError as e:
            logger.error(f"Missing required field in card: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing activity cards: {e}", exc_info=True)
            return []

    def _parse_timestamp(self, timestamp: str) -> int:
        parts = timestamp.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0

    def _parse_time_string(self, time_str: str, base_date=None) -> int:
        try:
            dt = datetime.strptime(time_str, "%I:%M %p")
            if base_date is None:
                base_date = datetime.now().date()
            result = datetime.combine(base_date, dt.time())
            return int(result.timestamp())
        except Exception as e:
            logger.error(f"Error parsing time string '{time_str}': {e}")
            return int(datetime.now().timestamp())

    def _format_observations(self, observations: List[Observation]) -> str:
        lines = []
        for obs in observations:
            start_time = self._format_timestamp(obs.start_ts)
            end_time = self._format_timestamp(obs.end_ts)
            lines.append(f"[{start_time} - {end_time}]: {obs.observation}")
        return "\n".join(lines)

    def _format_timestamp(self, ts: int) -> str:
        return datetime.fromtimestamp(ts).strftime("%I:%M %p").lstrip('0')

    def _transcribe_batch_images(self, batch_id: int, video_chunks: List, start_ts: int, duration_string: str) -> Optional[str]:
        """图片模式下的 Stage 1：抽帧去重后送图片列表给 LLM，返回 response 字符串，出错或无帧返回 None"""
        frames = self._extract_frames_from_chunks(video_chunks)
        logger.info(f"[Stage 1] Batch {batch_id}: image mode, extracted {len(frames)} deduped frames")
        if not frames:
            logger.info(f"[Stage 1] Batch {batch_id}: all frames deduped, marking TRANSCRIBED with no observations")
            self.db.update_batch_status(batch_id, BatchStatus.TRANSCRIBED)
            for chunk in video_chunks:
                self.db.update_chunk_status(chunk.id, ChunkStatus.COMPLETED)
            return None

        frames_with_ts = [
            (jpeg_bytes, datetime.fromtimestamp(ts).strftime("%H:%M:%S"))
            for jpeg_bytes, ts in frames
        ]
        prompt = get_transcription_prompt_images(duration_string, len(frames_with_ts))
        logger.info(f"[Stage 1] Transcribing batch {batch_id} via images ({duration_string}, {len(frames_with_ts)} frames)...")
        return chat_with_images(frames_with_ts, prompt, self.model)

    def _extract_frames_from_chunks(self, chunks: List) -> List[Tuple[bytes, int]]:
        """从 chunk 视频文件中逐帧抽取并去重，返回 [(jpeg_bytes, absolute_timestamp_int), ...]"""
        import cv2
        import numpy as np

        threshold = get_config().recording.static_diff_threshold
        results: List[Tuple[bytes, int]] = []
        prev_small_gray = None

        for chunk in chunks:
            if not chunk.file_path:
                continue
            cap = cv2.VideoCapture(chunk.file_path)
            if not cap.isOpened():
                logger.warning(f"[extract_frames] Cannot open {chunk.file_path}")
                continue

            fps = cap.get(cv2.CAP_PROP_FPS) or 1.0
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                abs_ts = int(chunk.start_ts + frame_idx / fps)
                frame_idx += 1

                small = cv2.resize(frame, (64, 36))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)

                if prev_small_gray is not None:
                    diff = float(np.mean(np.abs(gray - prev_small_gray)))
                    if diff < threshold:
                        continue

                prev_small_gray = gray
                ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ok:
                    results.append((buf.tobytes(), abs_ts))

            cap.release()

        return results

    def _merge_videos(self, chunks: List) -> str:
        import cv2

        if not chunks:
            raise ValueError("No chunks to merge")

        start_ts = chunks[0].start_ts
        timestamp = datetime.fromtimestamp(start_ts).strftime("%Y%m%d_%H%M%S")
        output_path = Path(get_config().recording.output_dir) / f"batch_{timestamp}.mp4"

        first_video = cv2.VideoCapture(chunks[0].file_path)
        fps = first_video.get(cv2.CAP_PROP_FPS)
        width = int(first_video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(first_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        first_video.release()

        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not out.isOpened():
            logger.warning("avc1 codec not available, trying H264...")
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not out.isOpened():
            logger.warning("H264 codec not available, falling back to mp4v")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not out.isOpened():
            raise RuntimeError(f"Failed to create video writer for {output_path}")

        try:
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
        try:
            retention_days = get_config().retention.days
            self.db.delete_old_chunks(retention_days)
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}", exc_info=True)

    def trigger_analysis_now(self):
        logger.info("Triggering immediate analysis...")
        try:
            self._run_stage1()
            self._run_stage2()
        except Exception as e:
            logger.error(f"Error in triggered analysis: {e}", exc_info=True)

    def reprocess_day(self, day: str) -> dict:
        try:
            logger.info(f"Reprocessing day: {day}")
            video_paths = self.db.delete_timeline_cards_by_day(day)

            for path in video_paths:
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception as e:
                    logger.error(f"Error deleting video {path}: {e}")

            batches = self.db.get_batches_by_day(day)
            for batch in batches:
                if batch.id is not None:
                    self.db.update_batch_status(batch.id, BatchStatus.PENDING)

            self.trigger_analysis_now()

            return {"success": True, "message": f"Reprocessing {len(batches)} batches for {day}"}

        except Exception as e:
            logger.error(f"Error reprocessing day {day}: {e}", exc_info=True)
            return {"success": False, "message": str(e)}
