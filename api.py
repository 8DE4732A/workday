"""
FastAPI Web 服务
提供 RESTful API 用于管理工作时间记录
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import uvicorn
import threading
import os
import re

from config_manager import config
from database import Database
from recorder import RecordingManager, ScreenRecorder
from analysis import AnalysisManager
from logger import get_logger

logger = get_logger(__name__)


# 初始化
db = Database(config.database.path)
recording_manager = RecordingManager(db)
analysis_manager = AnalysisManager(db)

# 创建 FastAPI 应用
app = FastAPI(
    title="Workday API",
    description="工作时间记录和分析 API",
    version="0.1.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 数据模型 ============

class RecordingStatus(BaseModel):
    is_recording: bool
    output_dir: str
    chunk_duration: int
    capture_interval: int


class TimelineCardResponse(BaseModel):
    id: int
    batch_id: int
    title: str
    description: str
    start_ts: int
    end_ts: int
    category: str
    video_path: Optional[str]
    duration: float


class StatsResponse(BaseModel):
    chunks: int
    batches: int
    timeline_cards: int


class ReprocessRequest(BaseModel):
    day: str


# ============ API 路由 ============

@app.get("/api")
async def api_root():
    """API 根路由"""
    return {
        "name": "Workday API",
        "version": "0.1.0",
        "status": "running"
    }


# ===== 录制管理 =====

@app.post("/recording/start")
async def start_recording(background_tasks: BackgroundTasks):
    """启动屏幕录制"""
    try:
        # 在后台启动录制
        background_tasks.add_task(recording_manager.start)

        return {
            "success": True,
            "message": "Recording started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recording/stop")
async def stop_recording():
    """停止屏幕录制"""
    try:
        recording_manager.stop()
        return {
            "success": True,
            "message": "Recording stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recording/status", response_model=RecordingStatus)
async def get_recording_status():
    """获取录制状态"""
    try:
        status = recording_manager.get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recording/monitors")
async def list_monitors():
    """列出所有可用的显示器"""
    try:
        monitors = ScreenRecorder.list_monitors()
        return {
            "success": True,
            "monitors": monitors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 分析管理 =====

@app.post("/analysis/start")
async def start_analysis():
    """启动分析服务"""
    try:
        analysis_manager.start()
        return {
            "success": True,
            "message": "Analysis service started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analysis/stop")
async def stop_analysis():
    """停止分析服务"""
    try:
        analysis_manager.stop()
        return {
            "success": True,
            "message": "Analysis service stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analysis/trigger")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """立即触发分析"""
    try:
        background_tasks.add_task(analysis_manager.trigger_analysis_now)
        return {
            "success": True,
            "message": "Analysis triggered"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analysis/reprocess")
async def reprocess_day(request: ReprocessRequest, background_tasks: BackgroundTasks):
    """重新处理指定日期的数据"""
    try:
        result = analysis_manager.reprocess_day(request.day)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 时间线数据 =====

@app.get("/timeline/today", response_model=List[TimelineCardResponse])
async def get_today_timeline():
    """获取今天的时间线"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        cards = db.get_timeline_cards_by_day(today)

        return [
            TimelineCardResponse(
                id=card.id,
                batch_id=card.batch_id,
                title=card.title,
                description=card.description,
                start_ts=card.start_ts,
                end_ts=card.end_ts,
                category=card.category,
                video_path=card.video_path,
                duration=card.duration
            )
            for card in cards
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/timeline/day/{day}", response_model=List[TimelineCardResponse])
async def get_day_timeline(day: str):
    """
    获取指定日期的时间线

    Args:
        day: 日期字符串 (YYYY-MM-DD)
    """
    try:
        cards = db.get_timeline_cards_by_day(day)

        return [
            TimelineCardResponse(
                id=card.id,
                batch_id=card.batch_id,
                title=card.title,
                description=card.description,
                start_ts=card.start_ts,
                end_ts=card.end_ts,
                category=card.category,
                video_path=card.video_path,
                duration=card.duration
            )
            for card in cards
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/timeline/range")
async def get_timeline_range(start_ts: int, end_ts: int):
    """
    获取时间范围内的时间线

    Args:
        start_ts: 开始时间戳
        end_ts: 结束时间戳
    """
    try:
        cards = db.get_timeline_cards_by_time_range(start_ts, end_ts)

        return [
            TimelineCardResponse(
                id=card.id,
                batch_id=card.batch_id,
                title=card.title,
                description=card.description,
                start_ts=card.start_ts,
                end_ts=card.end_ts,
                category=card.category,
                video_path=card.video_path,
                duration=card.duration
            )
            for card in cards
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 统计信息 =====

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """获取统计信息"""
    try:
        stats = db.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 配置管理 =====

class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    key: str
    value: str


class ConfigBatchUpdateRequest(BaseModel):
    """批量配置更新请求"""
    configs: dict  # {key: value}


@app.get("/config")
async def get_config(mask_sensitive: bool = True):
    """
    获取当前配置（嵌套格式）

    Args:
        mask_sensitive: 是否掩码敏感信息（默认为 True）
    """
    try:
        return config.to_dict(mask_sensitive=mask_sensitive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/all")
async def get_all_configs(mask_sensitive: bool = True):
    """
    获取所有配置及元数据

    Args:
        mask_sensitive: 是否掩码敏感信息（默认为 True）
    """
    try:
        return config.get_all_with_metadata(mask_sensitive=mask_sensitive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/category/{category}")
async def get_configs_by_category(category: str, mask_sensitive: bool = True):
    """
    根据分类获取配置

    Args:
        category: 配置分类
        mask_sensitive: 是否掩码敏感信息（默认为 True）
    """
    try:
        db = Database(config.database.path)
        configs = db.get_configs_by_category(category)

        # 掩码敏感配置
        if mask_sensitive:
            for cfg in configs:
                if cfg['key'] in config.SENSITIVE_KEYS:
                    cfg['value'] = config.mask_value(cfg['value'])
                    cfg['is_sensitive'] = True
                else:
                    cfg['is_sensitive'] = False
        else:
            for cfg in configs:
                cfg['is_sensitive'] = cfg['key'] in config.SENSITIVE_KEYS

        return {"category": category, "configs": configs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/{key}")
async def get_config_item(key: str, mask_sensitive: bool = True):
    """
    获取单个配置项

    Args:
        key: 配置键
        mask_sensitive: 是否掩码敏感信息（默认为 True）
    """
    try:
        value = config.get(key)
        if value is None:
            raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")

        # 掩码敏感值
        is_sensitive = key in config.SENSITIVE_KEYS
        if mask_sensitive and is_sensitive:
            display_value = config.mask_value(str(value))
        else:
            display_value = value

        # 获取元数据
        db = Database(config.database.path)
        config_item = db.get_config(key)

        return {
            "key": key,
            "value": display_value,
            "is_sensitive": is_sensitive,
            "metadata": config_item
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/config/{key}")
async def update_config_item(key: str, request: ConfigUpdateRequest):
    """更新单个配置项"""
    try:
        config.set(request.key, request.value)
        return {
            "success": True,
            "message": f"Config '{key}' updated successfully",
            "key": key,
            "value": request.value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/batch")
async def batch_update_configs(request: ConfigBatchUpdateRequest):
    """批量更新配置"""
    try:
        updated = []
        errors = []

        for key, value in request.configs.items():
            try:
                config.set(key, value)
                updated.append(key)
            except Exception as e:
                errors.append({"key": key, "error": str(e)})

        return {
            "success": len(errors) == 0,
            "updated": updated,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/reload")
async def reload_config():
    """重新加载配置"""
    try:
        config.reload()
        return {
            "success": True,
            "message": "Configuration reloaded from database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 调试和数据管理 =====

class ClearDataRequest(BaseModel):
    """清除数据请求"""
    keep_videos: bool = False  # 是否保留视频文件


@app.post("/data/clear")
async def clear_all_data(request: ClearDataRequest):
    """
    清空所有数据（保留配置）

    Args:
        keep_videos: 是否保留视频文件
    """
    try:
        result = db.clear_all_data(keep_videos=request.keep_videos)
        return result
    except Exception as e:
        logger.error(f"Error clearing data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/token/today")
async def get_today_token_usage():
    """获取今天的 Token 使用统计"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        usage = db.get_token_usage_by_day(today)
        return {
            "date": today,
            **usage
        }
    except Exception as e:
        logger.error(f"Error getting token usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/token/range")
async def get_token_usage_range(start_date: str, end_date: str):
    """
    获取日期范围内的 Token 使用统计

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    """
    try:
        usage = db.get_token_usage_by_date_range(start_date, end_date)
        return {
            "start_date": start_date,
            "end_date": end_date,
            "daily_usage": usage,
            "total": {
                "prompt_tokens": sum(d['prompt_tokens'] for d in usage),
                "completion_tokens": sum(d['completion_tokens'] for d in usage),
                "total_tokens": sum(d['total_tokens'] for d in usage),
                "request_count": sum(d['request_count'] for d in usage)
            }
        }
    except Exception as e:
        logger.error(f"Error getting token usage range: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats/token/records")
async def get_token_usage_records(date: Optional[str] = None, limit: int = 100, offset: int = 0):
    """
    获取详细的 Token 使用记录列表

    Args:
        date: 可选的日期过滤 (YYYY-MM-DD)
        limit: 返回的记录数量 (默认 100)
        offset: 偏移量，用于分页 (默认 0)
    """
    try:
        records = db.get_token_usage_records(date=date, limit=limit, offset=offset)
        total = db.get_token_usage_count(date=date)

        return {
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting token usage records: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ===== 视频文件 =====

def ranged_file_generator(file_path: Path, start: int, end: int, chunk_size: int = 8192):
    """
    生成指定范围的文件数据流

    Args:
        file_path: 文件路径
        start: 起始字节位置
        end: 结束字节位置
        chunk_size: 每次读取的块大小
    """
    try:
        with open(file_path, 'rb') as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                try:
                    yield chunk
                except (ConnectionError, ConnectionResetError):
                    # 客户端主动关闭连接（正常行为，如浏览器只需要部分数据）
                    logger.debug(f"Client closed connection while streaming {file_path.name}")
                    break
    except Exception as e:
        logger.error(f"Error in ranged_file_generator for {file_path}: {e}")
        raise


@app.get("/video/{video_id}")
async def get_video(video_id: int, request: Request):
    """获取视频文件（支持Range请求）"""
    try:
        # 根据 timeline card ID 查询视频路径
        card = db.get_timeline_card_by_id(video_id)

        if not card:
            raise HTTPException(status_code=404, detail="Timeline card not found")

        if not card.video_path:
            raise HTTPException(status_code=404, detail="Video file not found for this card")

        # 检查视频文件是否存在
        video_file = Path(card.video_path)
        if not video_file.exists():
            raise HTTPException(status_code=404, detail=f"Video file does not exist: {card.video_path}")

        # 获取文件大小
        file_size = video_file.stat().st_size

        # 解析Range请求头
        range_header = request.headers.get('range')

        if range_header:
            # 解析 Range: bytes=start-end
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if not match:
                raise HTTPException(status_code=416, detail="Invalid range header")

            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else file_size - 1

            # 验证范围
            if start >= file_size or end >= file_size or start > end:
                raise HTTPException(
                    status_code=416,
                    detail="Requested range not satisfiable",
                    headers={"Content-Range": f"bytes */{file_size}"}
                )

            # 返回部分内容
            content_length = end - start + 1
            headers = {
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(content_length),
                'Content-Type': 'video/mp4',
            }

            return StreamingResponse(
                ranged_file_generator(video_file, start, end),
                status_code=206,
                headers=headers,
                media_type='video/mp4'
            )
        else:
            # 返回完整文件
            headers = {
                'Accept-Ranges': 'bytes',
                'Content-Length': str(file_size),
                'Content-Type': 'video/mp4',
            }

            return StreamingResponse(
                ranged_file_generator(video_file, 0, file_size - 1),
                headers=headers,
                media_type='video/mp4'
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving video {video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 静态文件服务 ============
# 注意：这个必须放在所有 API 路由之后，作为 catch-all 路由

def setup_static_files():
    """设置静态文件服务"""
    web_dir = Path("./web/out")

    if not web_dir.exists():
        logger.warning(f"Web directory not found: {web_dir}")
        logger.warning("Please run 'cd web && npm install && npm run build' to build the frontend.")
        return False

    # 检查是否有 index.html
    if not (web_dir / "index.html").exists():
        logger.warning(f"index.html not found in {web_dir}")
        return False

    # 挂载 Next.js 静态资源目录
    next_dir = web_dir / "_next"
    if next_dir.exists():
        app.mount("/_next", StaticFiles(directory=next_dir), name="nextjs-static")
        logger.info(f"Mounted Next.js static files from {next_dir}")

    logger.info(f"Static file serving enabled from {web_dir}")
    return True

# 在所有 API 路由定义后，检查并设置静态文件
_static_enabled = False


# ============ 启动事件 ============

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info("Workday API starting up...")

    # 设置静态文件服务
    global _static_enabled
    _static_enabled = setup_static_files()

    # 自动启动分析服务
    analysis_manager.start()

    logger.info("Workday API ready!")
    if _static_enabled:
        logger.info("Access the web interface at http://localhost:8000")
    else:
        logger.info("API only mode - web interface not available")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("Workday API shutting down...")

    # 停止服务
    recording_manager.stop()
    analysis_manager.stop()

    logger.info("Workday API stopped")


# ============ Catch-all 路由（必须在最后）============

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """服务单页应用和静态文件"""
    if not _static_enabled:
        # 如果静态文件未启用，返回 API 信息
        return {
            "name": "Workday API",
            "version": "0.1.0",
            "status": "running",
            "message": "Web interface not available. Please build the frontend first.",
            "build_instructions": "cd web && npm install && npm run build"
        }

    web_dir = Path("./web/out")

    # 空路径或根路径
    if not full_path or full_path == "/":
        index_path = web_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

    # 尝试查找文件
    file_path = web_dir / full_path

    # 如果是目录，查找 index.html
    if file_path.is_dir():
        index_file = file_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

    # 如果文件存在，返回文件
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # SPA 回退：对于未找到的路径，返回 index.html（前端路由会处理）
    index_path = web_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    # 如果连 index.html 都没有，返回 404
    raise HTTPException(status_code=404, detail="File not found")


# ============ 主函数 ============

def run_server():
    """运行服务器"""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.api.port,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
