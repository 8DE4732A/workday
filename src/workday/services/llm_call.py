import base64
import json
import re
import urllib.request
from typing import List, Tuple

from openai import OpenAI

from workday.core.logger import get_logger
from workday.core.config import get_config

logger = get_logger(__name__)

_cached_client: OpenAI | None = None
_cached_api_base = None
_cached_api_key = None
_db = None


def _get_db():
    global _db
    if _db is None:
        from workday.core.database import Database
        _db = Database(get_config().database.path)
    return _db


def _record_token_usage(usage, request_type: str, model: str, batch_id: int | None = None):
    try:
        if usage:
            prompt = getattr(usage, 'prompt_tokens', 0) or 0
            completion = getattr(usage, 'completion_tokens', 0) or 0
            _get_db().insert_token_usage(
                request_type=request_type,
                model=model,
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=prompt + completion,
                batch_id=batch_id
            )
    except Exception as e:
        logger.warning(f"Failed to record token usage: {e}")


def clean_json_response(content: str) -> str:
    content = content.strip()
    match = re.match(r'^```(?:json)?\s*\n(.*?)\n```$', content, re.DOTALL)
    return match.group(1).strip() if match else content


def get_client() -> OpenAI:
    global _cached_client, _cached_api_base, _cached_api_key

    cfg = get_config().llm
    api_base = cfg.api_base.rstrip('/')
    api_key = cfg.api_key

    if (_cached_client is None
            or _cached_api_base != api_base
            or _cached_api_key != api_key):
        logger.info("Initializing LLM client")
        _cached_client = OpenAI(
            base_url=api_base,
            api_key=api_key or "placeholder",
        )
        _cached_api_base = api_base
        _cached_api_key = api_key

    return _cached_client


def fetch_available_models(api_base: str, api_key: str) -> list[str]:
    base = api_base.rstrip('/')
    # 优先尝试 /v1/models，再回退到 /models
    for url in (f"{base}/v1/models", f"{base}/models"):
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {api_key}'})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                models = data.get('data', [])
                return [m['id'] for m in models if isinstance(m, dict) and 'id' in m]
        except Exception:
            continue
    logger.warning("fetch_available_models: both /v1/models and /models failed")
    return []


def chat_with_video(video_path: str, prompt: str, model: str = '') -> str:
    cfg = get_config().llm
    model = model or cfg.model
    debug = get_config().analysis.debug_mode

    logger.info(f"[chat_with_video] model={model}, video={video_path}")
    if debug:
        logger.debug(f"[chat_with_video] prompt=\n{prompt}")

    with open(video_path, 'rb') as f:
        video_bytes = f.read()
    video_base64 = base64.b64encode(video_bytes).decode('utf-8')
    logger.debug(f"[chat_with_video] video size={len(video_bytes)/1024:.1f}KB, base64={len(video_base64)//1024}KB")

    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "video_url",
                    "video_url": {"url": f"data:video/mp4;base64,{video_base64}"},
                    "fps": 1,
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )
    content = response.choices[0].message.content or ""
    usage = response.usage
    if usage:
        _record_token_usage(usage, 'chat_with_video', model)
        logger.info(f"[chat_with_video] tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

    logger.debug(f"[chat_with_video] response length={len(content)}")
    if debug:
        logger.debug(f"[chat_with_video] response=\n{content}")

    return clean_json_response(content)


def transcribe_video(video_path: str, prompt: str, model: str = '') -> str:
    """第一阶段：视频转录 - 生成 Observations"""
    logger.info(f"[transcribe_video] start video={video_path}, model={model}")
    result = chat_with_video(video_path, prompt, model)
    logger.info("[transcribe_video] completed")
    return result


def chat_with_images(frames: List[Tuple[bytes, str]], prompt: str, model: str = '') -> str:
    """图片模式下的 Stage 1 调用；frames 为 [(jpeg_bytes, 'HH:MM:SS'), ...]"""
    cfg = get_config().llm
    model = model or cfg.model
    debug = get_config().analysis.debug_mode

    logger.info(f"[chat_with_images] model={model}, frames={len(frames)}")
    if debug:
        logger.debug(f"[chat_with_images] prompt=\n{prompt}")

    content = []
    for jpeg_bytes, ts in frames:
        b64 = base64.b64encode(jpeg_bytes).decode('utf-8')
        content.append({"type": "text", "text": f"Frame at {ts}:"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    content.append({"type": "text", "text": prompt})

    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
    )
    result = response.choices[0].message.content or ""
    usage = response.usage
    if usage:
        _record_token_usage(usage, 'chat_with_images', model)
        logger.info(f"[chat_with_images] tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

    logger.debug(f"[chat_with_images] response length={len(result)}")
    if debug:
        logger.debug(f"[chat_with_images] response=\n{result}")

    return clean_json_response(result)


def generate_activity_cards(prompt: str, model: str = '', request_type: str = 'generate_activity_cards') -> str:
    """第二阶段：生成活动卡片 - 基于 Observations"""
    model = model or get_config().llm.model
    debug = get_config().analysis.debug_mode

    logger.info(f"[generate_activity_cards] model={model}")
    if debug:
        logger.debug(f"[generate_activity_cards] prompt=\n{prompt}")

    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content or ""
    usage = response.usage
    if usage:
        _record_token_usage(usage, request_type, model)
        logger.info(f"[generate_activity_cards] tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")

    logger.debug(f"[generate_activity_cards] response length={len(content)}")
    if debug:
        logger.debug(f"[generate_activity_cards] response=\n{content}")

    return clean_json_response(content)


def generate_analysis_summary(prompt: str, model: str = '') -> str:
    """生成分析报告摘要 - 纯文本 chat completion"""
    return generate_activity_cards(prompt, model=model, request_type='analysis_report')
