"""
数据库管理模块
使用 SQLite 存储录制数据和分析结果
"""
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from models import RecordingChunk, Batch, TimelineCard, Observation, ChunkStatus, BatchStatus, INIT_SQL
from logger import get_logger

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
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ============ RecordingChunk 操作 ============

    def insert_chunk(self, chunk: RecordingChunk) -> int:
        """插入录制片段"""
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
        """更新片段状态"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE recording_chunks SET status = ? WHERE id = ?",
                (status, chunk_id)
            )
            conn.commit()

    def get_pending_chunks(self, limit: int = 100) -> List[RecordingChunk]:
        """获取待处理的片段"""
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
        """根据时间范围获取片段"""
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
        """删除旧片段（默认3天前）"""
        cutoff_ts = int((datetime.now() - timedelta(days=days)).timestamp())

        with self._get_conn() as conn:
            # 获取要删除的文件路径
            rows = conn.execute(
                "SELECT file_path FROM recording_chunks WHERE end_ts < ?",
                (cutoff_ts,)
            ).fetchall()

            file_paths = [row['file_path'] for row in rows]

            # 删除数据库记录
            conn.execute("DELETE FROM recording_chunks WHERE end_ts < ?", (cutoff_ts,))
            conn.commit()

            # 删除文件
            for path in file_paths:
                try:
                    Path(path).unlink(missing_ok=True)
                except Exception as e:
                    logger.error(f"Error deleting file {path}: {e}")

    # ============ Batch 操作 ============

    def insert_batch(self, batch: Batch) -> int:
        """插入分析批次"""
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
        """更新批次状态"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE batches SET status = ? WHERE id = ?",
                (status, batch_id)
            )
            conn.commit()

    def get_pending_batches(self) -> List[Batch]:
        """获取待处理的批次"""
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
        """根据日期获取批次"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM batches WHERE day = ? ORDER BY start_ts ASC",
                (day,)
            ).fetchall()

            return [self._row_to_batch(row) for row in rows]

    # ============ Observation 操作 ============

    def insert_observation(self, obs: Observation) -> int:
        """插入观察记录"""
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
        """批量插入观察记录"""
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
        """根据批次ID获取观察记录"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM observations WHERE batch_id = ? ORDER BY start_ts ASC",
                (batch_id,)
            ).fetchall()

            return [self._row_to_observation(row) for row in rows]

    def get_observations_by_time_range(self, start_ts: int, end_ts: int) -> List[Observation]:
        """根据时间范围获取观察记录"""
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
        """插入时间线卡片"""
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
        """根据日期获取时间线卡片"""
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
        """根据时间范围获取时间线卡片"""
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
        """根据 ID 获取时间线卡片"""
        with self._get_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM timeline_cards
                WHERE id = ?
                """,
                (card_id,)
            ).fetchone()

            if row:
                return self._row_to_timeline_card(row)
            return None

    def delete_timeline_cards_by_day(self, day: str) -> List[str]:
        """删除指定日期的时间线卡片，返回视频路径列表"""
        with self._get_conn() as conn:
            # 获取要删除的视频路径
            rows = conn.execute(
                """
                SELECT tc.video_path FROM timeline_cards tc
                JOIN batches b ON tc.batch_id = b.id
                WHERE b.day = ? AND tc.video_path IS NOT NULL
                """,
                (day,)
            ).fetchall()

            video_paths = [row['video_path'] for row in rows]

            # 删除卡片
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
        """将数据库行转换为 RecordingChunk"""
        return RecordingChunk(
            id=row['id'],
            start_ts=row['start_ts'],
            end_ts=row['end_ts'],
            file_path=row['file_path'],
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def _row_to_batch(self, row: sqlite3.Row) -> Batch:
        """将数据库行转换为 Batch"""
        return Batch(
            id=row['id'],
            day=row['day'],
            start_ts=row['start_ts'],
            end_ts=row['end_ts'],
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def _row_to_observation(self, row: sqlite3.Row) -> Observation:
        """将数据库行转换为 Observation"""
        return Observation(
            id=row['id'],
            batch_id=row['batch_id'],
            start_ts=row['start_ts'],
            end_ts=row['end_ts'],
            observation=row['observation'],
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def _row_to_timeline_card(self, row: sqlite3.Row) -> TimelineCard:
        """将数据库行转换为 TimelineCard"""
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
        """获取数据库统计信息"""
        with self._get_conn() as conn:
            chunks_count = conn.execute("SELECT COUNT(*) FROM recording_chunks").fetchone()[0]
            batches_count = conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0]
            observations_count = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            cards_count = conn.execute("SELECT COUNT(*) FROM timeline_cards").fetchone()[0]

            return {
                "chunks": chunks_count,
                "batches": batches_count,
                "observations": observations_count,
                "timeline_cards": cards_count
            }

    # ============ Config 操作 ============

    def get_config(self, key: str) -> Optional[dict]:
        """
        获取单个配置项

        Args:
            key: 配置键

        Returns:
            配置字典或 None
        """
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
        """
        获取所有配置项

        Returns:
            配置字典 {key: value}
        """
        with self._get_conn() as conn:
            rows = conn.execute("SELECT key, value, type FROM config").fetchall()

            configs = {}
            for row in rows:
                key = row['key']
                value = row['value']
                value_type = row['type']

                # 根据类型转换值
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
        """
        根据分类获取配置项

        Args:
            category: 配置分类

        Returns:
            配置列表
        """
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
        """
        设置配置项（插入或更新）

        Args:
            key: 配置键
            value: 配置值（字符串形式）
            value_type: 值类型 (string, int, float, bool)
            category: 配置分类
            description: 配置描述
        """
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
        """
        批量设置配置项

        Args:
            configs: 配置列表，每个元素是字典 {key, value, type, category, description}
        """
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
        """
        删除配置项

        Args:
            key: 配置键
        """
        with self._get_conn() as conn:
            conn.execute("DELETE FROM config WHERE key = ?", (key,))
            conn.commit()

    def config_exists(self) -> bool:
        """
        检查是否已有配置项（用于判断是否需要初始化）

        Returns:
            是否存在配置项
        """
        with self._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM config").fetchone()[0]
            return count > 0

    # ============ Token Usage 操作 ============

    def insert_token_usage(self, request_type: str, model: str,
                          prompt_tokens: int, completion_tokens: int,
                          total_tokens: int, batch_id: Optional[int] = None) -> int:
        """
        记录token使用情况

        Args:
            request_type: 请求类型 ('transcribe' 或 'generate_cards')
            model: 模型名称
            prompt_tokens: 提示词token数
            completion_tokens: 完成token数
            total_tokens: 总token数
            batch_id: 关联的batch ID

        Returns:
            插入的记录ID
        """
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
        """
        获取某天的token使用统计

        Args:
            day: 日期字符串 (YYYY-MM-DD)

        Returns:
            统计字典 {prompt_tokens, completion_tokens, total_tokens, request_count}
        """
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
        """
        获取日期范围内的token使用统计（按天分组）

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            统计列表，每项包含日期和使用情况
        """
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

    def get_token_usage_records(self, date: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[dict]:
        """
        获取详细的 token 使用记录列表

        Args:
            date: 可选的日期过滤 (YYYY-MM-DD)，如果为 None 则返回所有记录
            limit: 返回的记录数量
            offset: 偏移量（用于分页）

        Returns:
            token 使用记录列表
        """
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
        """
        获取 token 使用记录的总数

        Args:
            date: 可选的日期过滤 (YYYY-MM-DD)

        Returns:
            记录总数
        """
        with self._get_conn() as conn:
            if date:
                count = conn.execute(
                    "SELECT COUNT(*) FROM token_usage WHERE DATE(created_at) = ?",
                    (date,)
                ).fetchone()[0]
            else:
                count = conn.execute("SELECT COUNT(*) FROM token_usage").fetchone()[0]
            return count

    # ============ 数据清理操作 ============

    def clear_all_data(self, keep_videos: bool = False) -> dict:
        """
        清空所有数据（保留配置）

        Args:
            keep_videos: 是否保留视频文件

        Returns:
            清理结果统计
        """
        import os
        from pathlib import Path

        deleted_videos = []

        with self._get_conn() as conn:
            # 获取要删除的视频文件路径
            if not keep_videos:
                # 从chunks获取视频文件
                chunk_rows = conn.execute(
                    "SELECT file_path FROM recording_chunks WHERE file_path IS NOT NULL"
                ).fetchall()
                for row in chunk_rows:
                    if row['file_path']:
                        deleted_videos.append(row['file_path'])

                # 从batches获取合并视频
                batch_rows = conn.execute(
                    """
                    SELECT DISTINCT video_path FROM timeline_cards
                    WHERE video_path IS NOT NULL
                    """
                ).fetchall()
                for row in batch_rows:
                    if row['video_path']:
                        deleted_videos.append(row['video_path'])

            # 获取删除前的统计
            stats_before = {
                'chunks': conn.execute("SELECT COUNT(*) FROM recording_chunks").fetchone()[0],
                'batches': conn.execute("SELECT COUNT(*) FROM batches").fetchone()[0],
                'observations': conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
                'timeline_cards': conn.execute("SELECT COUNT(*) FROM timeline_cards").fetchone()[0],
                'token_usage': conn.execute("SELECT COUNT(*) FROM token_usage").fetchone()[0]
            }

            # 删除数据库记录（因为有外键约束，按顺序删除）
            conn.execute("DELETE FROM timeline_cards")
            conn.execute("DELETE FROM observations")
            conn.execute("DELETE FROM token_usage")
            conn.execute("DELETE FROM batches")
            conn.execute("DELETE FROM recording_chunks")
            conn.commit()

        # 删除视频文件
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
