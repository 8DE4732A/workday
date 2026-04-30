"""
数据库管理模块
使用 SQLite 存储录制数据和分析结果
"""
import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

from workday.core.models import (
    RecordingChunk, Batch, TimelineCard, Observation,
    ChunkStatus, BatchStatus, INIT_SQL
)
from workday.core.logger import get_logger

logger = get_logger(__name__)


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str = "workday.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(INIT_SQL)
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ============ RecordingChunk 操作 ============

    def insert_chunk(self, chunk: RecordingChunk) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO recording_chunks (start_ts, end_ts, file_path, status)
                VALUES (?, ?, ?, ?)
                """,
                (chunk.start_ts, chunk.end_ts, chunk.file_path, chunk.status)
            )
            conn.commit()
            return cursor.lastrowid

    def update_chunk_status(self, chunk_id: int, status: str):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE recording_chunks SET status = ? WHERE id = ?",
                (status, chunk_id)
            )
            conn.commit()

    def get_pending_chunks(self, limit: int = 100) -> List[RecordingChunk]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM recording_chunks
                WHERE status = ?
                ORDER BY start_ts ASC
                LIMIT ?
                """,
                (ChunkStatus.PENDING, limit)
            ).fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def get_chunks_by_time_range(self, start_ts: int, end_ts: int) -> List[RecordingChunk]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM recording_chunks
                WHERE start_ts >= ? AND end_ts <= ?
                ORDER BY start_ts ASC
                """,
                (start_ts, end_ts)
            ).fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def delete_old_chunks(self, days: int = 3):
        cutoff_ts = int((datetime.now() - timedelta(days=days)).timestamp())
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT file_path FROM recording_chunks WHERE end_ts < ?",
                (cutoff_ts,)
            ).fetchall()
            file_paths = [row['file_path'] for row in rows]
            conn.execute("DELETE FROM recording_chunks WHERE end_ts < ?", (cutoff_ts,))
            conn.commit()
            for path in file_paths:
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception as e:
                    logger.error(f"Error deleting file {path}: {e}")

    # ============ Batch 操作 ============

    def insert_batch(self, batch: Batch) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO batches (day, start_ts, end_ts, status)
                VALUES (?, ?, ?, ?)
                """,
                (batch.day, batch.start_ts, batch.end_ts, batch.status)
            )
            conn.commit()
            return cursor.lastrowid

    def update_batch_status(self, batch_id: int, status: str):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE batches SET status = ? WHERE id = ?",
                (status, batch_id)
            )
            conn.commit()

    def get_pending_batches(self) -> List[Batch]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM batches
                WHERE status = ?
                ORDER BY start_ts ASC
                """,
                (BatchStatus.PENDING,)
            ).fetchall()
            return [self._row_to_batch(row) for row in rows]

    def get_batches_by_day(self, day: str) -> List[Batch]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM batches WHERE day = ? ORDER BY start_ts ASC",
                (day,)
            ).fetchall()
            return [self._row_to_batch(row) for row in rows]

    # ============ Observation 操作 ============

    def insert_observation(self, obs: Observation) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO observations (batch_id, start_ts, end_ts, observation)
                VALUES (?, ?, ?, ?)
                """,
                (obs.batch_id, obs.start_ts, obs.end_ts, obs.observation)
            )
            conn.commit()
            return cursor.lastrowid

    def insert_observations(self, observations: List[Observation]):
        with self._get_conn() as conn:
            conn.executemany(
                """
                INSERT INTO observations (batch_id, start_ts, end_ts, observation)
                VALUES (?, ?, ?, ?)
                """,
                [(obs.batch_id, obs.start_ts, obs.end_ts, obs.observation) for obs in observations]
            )
            conn.commit()

    def get_observations_by_batch(self, batch_id: int) -> List[Observation]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM observations WHERE batch_id = ? ORDER BY start_ts ASC",
                (batch_id,)
            ).fetchall()
            return [self._row_to_observation(row) for row in rows]

    def get_observations_by_time_range(self, start_ts: int, end_ts: int) -> List[Observation]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM observations
                WHERE start_ts >= ? AND end_ts <= ?
                ORDER BY start_ts ASC
                """,
                (start_ts, end_ts)
            ).fetchall()
            return [self._row_to_observation(row) for row in rows]

    # ============ TimelineCard 操作 ============

    def insert_timeline_card(self, card: TimelineCard) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO timeline_cards
                (batch_id, title, description, start_ts, end_ts, category, video_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (card.batch_id, card.title, card.description,
                 card.start_ts, card.end_ts, card.category, card.video_path)
            )
            conn.commit()
            return cursor.lastrowid

    def get_timeline_cards_by_day(self, day: str) -> List[TimelineCard]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT tc.* FROM timeline_cards tc
                JOIN batches b ON tc.batch_id = b.id
                WHERE b.day = ?
                ORDER BY tc.start_ts ASC
                """,
                (day,)
            ).fetchall()
            return [self._row_to_timeline_card(row) for row in rows]

    def get_timeline_cards_by_time_range(self, start_ts: int, end_ts: int) -> List[TimelineCard]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM timeline_cards
                WHERE start_ts >= ? AND end_ts <= ?
                ORDER BY start_ts ASC
                """,
                (start_ts, end_ts)
            ).fetchall()
            return [self._row_to_timeline_card(row) for row in rows]

    def get_timeline_card_by_id(self, card_id: int) -> Optional[TimelineCard]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM timeline_cards WHERE id = ?",
                (card_id,)
            ).fetchone()
            if row:
                return self._row_to_timeline_card(row)
            return None

    def delete_timeline_cards_by_day(self, day: str) -> List[str]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT tc.video_path FROM timeline_cards tc
                JOIN batches b ON tc.batch_id = b.id
                WHERE b.day = ? AND tc.video_path IS NOT NULL
                """,
                (day,)
            ).fetchall()
            video_paths = [row['video_path'] for row in rows]
            conn.execute(
                """
                DELETE FROM timeline_cards
                WHERE batch_id IN (SELECT id FROM batches WHERE day = ?)
                """,
                (day,)
            )
            conn.commit()
            return video_paths

    # ============ 辅助方法 ============

    def _row_to_chunk(self, row: sqlite3.Row) -> RecordingChunk:
        return RecordingChunk(
            id=row['id'],
            start_ts=row['start_ts'],
            end_ts=row['end_ts'],
            file_path=row['file_path'],
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def _row_to_batch(self, row: sqlite3.Row) -> Batch:
        return Batch(
            id=row['id'],
            day=row['day'],
            start_ts=row['start_ts'],
            end_ts=row['end_ts'],
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def _row_to_observation(self, row: sqlite3.Row) -> Observation:
        return Observation(
            id=row['id'],
            batch_id=row['batch_id'],
            start_ts=row['start_ts'],
            end_ts=row['end_ts'],
            observation=row['observation'],
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def _row_to_timeline_card(self, row: sqlite3.Row) -> TimelineCard:
        return TimelineCard(
            id=row['id'],
            batch_id=row['batch_id'],
            title=row['title'],
            description=row['description'],
            start_ts=row['start_ts'],
            end_ts=row['end_ts'],
            category=row['category'],
            video_path=row['video_path'],
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def get_stats(self) -> dict:
        with self._get_conn() as conn:
            return {
                "chunks": conn.execute("SELECT COUNT(*) FROM recording_chunks").fetchone()[0],
                "batches": conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0],
                "observations": conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
                "timeline_cards": conn.execute("SELECT COUNT(*) FROM timeline_cards").fetchone()[0],
            }

    # ============ Config 操作 ============

    def get_config(self, key: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM config WHERE key = ?",
                (key,)
            ).fetchone()
            if row:
                return {
                    'key': row['key'],
                    'value': row['value'],
                    'type': row['type'],
                    'category': row['category'],
                    'description': row['description'],
                    'updated_at': row['updated_at']
                }
            return None

    def get_all_configs(self) -> dict:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT key, value, type FROM config").fetchall()
            configs = {}
            for row in rows:
                key = row['key']
                value = row['value']
                value_type = row['type']
                if value_type == 'int':
                    configs[key] = int(value)
                elif value_type == 'float':
                    configs[key] = float(value)
                elif value_type == 'bool':
                    configs[key] = value.lower() in ('true', '1', 'yes')
                else:
                    configs[key] = value
            return configs

    def get_configs_by_category(self, category: str) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM config WHERE category = ? ORDER BY key",
                (category,)
            ).fetchall()
            return [
                {
                    'key': row['key'],
                    'value': row['value'],
                    'type': row['type'],
                    'category': row['category'],
                    'description': row['description'],
                    'updated_at': row['updated_at']
                }
                for row in rows
            ]

    def set_config(self, key: str, value: str, value_type: str = 'string',
                   category: str = 'general', description: str = None):
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO config (key, value, type, category, description, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    type = excluded.type,
                    category = excluded.category,
                    description = excluded.description,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value, value_type, category, description)
            )
            conn.commit()

    def set_configs_batch(self, configs: List[dict]):
        with self._get_conn() as conn:
            for config in configs:
                conn.execute(
                    """
                    INSERT INTO config (key, value, type, category, description, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        type = excluded.type,
                        category = excluded.category,
                        description = excluded.description,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        config['key'],
                        config['value'],
                        config.get('type', 'string'),
                        config.get('category', 'general'),
                        config.get('description')
                    )
                )
            conn.commit()

    def delete_config(self, key: str):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM config WHERE key = ?", (key,))
            conn.commit()

    def config_exists(self) -> bool:
        with self._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM config").fetchone()[0]
            return count > 0

    # ============ Token Usage 操作 ============

    def insert_token_usage(self, request_type: str, model: str,
                           prompt_tokens: int, completion_tokens: int,
                           total_tokens: int, batch_id: Optional[int] = None) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO token_usage (request_type, model, prompt_tokens,
                                        completion_tokens, total_tokens, batch_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (request_type, model, prompt_tokens, completion_tokens, total_tokens, batch_id)
            )
            conn.commit()
            return cursor.lastrowid

    def get_token_usage_by_day(self, day: str) -> dict:
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COUNT(*) as request_count
                FROM token_usage
                WHERE DATE(created_at) = ?
                """,
                (day,)
            ).fetchone()
            return {
                'prompt_tokens': row['prompt_tokens'],
                'completion_tokens': row['completion_tokens'],
                'total_tokens': row['total_tokens'],
                'request_count': row['request_count']
            }

    def get_token_usage_by_date_range(self, start_date: str, end_date: str) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    DATE(created_at) as date,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(completion_tokens) as completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as request_count
                FROM token_usage
                WHERE DATE(created_at) BETWEEN ? AND ?
                GROUP BY DATE(created_at)
                ORDER BY date
                """,
                (start_date, end_date)
            ).fetchall()
            return [
                {
                    'date': row['date'],
                    'prompt_tokens': row['prompt_tokens'],
                    'completion_tokens': row['completion_tokens'],
                    'total_tokens': row['total_tokens'],
                    'request_count': row['request_count']
                }
                for row in rows
            ]

    def get_token_usage_records(self, date: Optional[str] = None,
                                limit: int = 100, offset: int = 0) -> List[dict]:
        with self._get_conn() as conn:
            if date:
                rows = conn.execute(
                    """
                    SELECT * FROM token_usage
                    WHERE DATE(created_at) = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (date, limit, offset)
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM token_usage
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                ).fetchall()
            return [
                {
                    'id': row['id'],
                    'request_type': row['request_type'],
                    'model': row['model'],
                    'prompt_tokens': row['prompt_tokens'],
                    'completion_tokens': row['completion_tokens'],
                    'total_tokens': row['total_tokens'],
                    'batch_id': row['batch_id'],
                    'created_at': row['created_at']
                }
                for row in rows
            ]

    def get_token_usage_count(self, date: Optional[str] = None) -> int:
        with self._get_conn() as conn:
            if date:
                return conn.execute(
                    "SELECT COUNT(*) FROM token_usage WHERE DATE(created_at) = ?",
                    (date,)
                ).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM token_usage").fetchone()[0]

    # ============ 数据清理操作 ============

    def clear_all_data(self, keep_videos: bool = False) -> dict:
        """清空所有数据（保留配置）"""
        deleted_videos = []

        with self._get_conn() as conn:
            if not keep_videos:
                chunk_rows = conn.execute(
                    "SELECT file_path FROM recording_chunks WHERE file_path IS NOT NULL"
                ).fetchall()
                for row in chunk_rows:
                    if row['file_path']:
                        deleted_videos.append(row['file_path'])

                batch_rows = conn.execute(
                    "SELECT DISTINCT video_path FROM timeline_cards WHERE video_path IS NOT NULL"
                ).fetchall()
                for row in batch_rows:
                    if row['video_path']:
                        deleted_videos.append(row['video_path'])

            stats_before = {
                'chunks': conn.execute("SELECT COUNT(*) FROM recording_chunks").fetchone()[0],
                'batches': conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0],
                'observations': conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
                'timeline_cards': conn.execute("SELECT COUNT(*) FROM timeline_cards").fetchone()[0],
                'token_usage': conn.execute("SELECT COUNT(*) FROM token_usage").fetchone()[0]
            }

            conn.execute("DELETE FROM timeline_cards")
            conn.execute("DELETE FROM observations")
            conn.execute("DELETE FROM token_usage")
            conn.execute("DELETE FROM batches")
            conn.execute("DELETE FROM recording_chunks")
            conn.commit()

        deleted_files_count = 0
        failed_files = []

        if not keep_videos:
            for video_path in deleted_videos:
                try:
                    file_path = Path(video_path)
                    if file_path.exists():
                        file_path.unlink()
                        deleted_files_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {video_path}: {e}")
                    failed_files.append(video_path)

        return {
            'success': True,
            'deleted': stats_before,
            'deleted_files': deleted_files_count,
            'failed_files': failed_files
        }
