import base64
import json
import re
import urllib.request

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from workday.core.logger import get_logger
from workday.core.config import get_config

logger = get_logger(__name__)

_cached_client = None
_cached_api_base = None
_cached_api_key = None
_db = None


def _get_db():
    global _db
    if _db is None:
        from workday.core.database import Database
        _db = Database(get_config().database.path)
    return _db


def _record_token_usage(usage, request_type: str, model: str, batch_id: int = None):
    try:
        if usage:
            prompt = getattr(usage, 'input_tokens', 0) or getattr(usage, 'prompt_tokens', 0)
            completion = getattr(usage, 'output_tokens', 0) or getattr(usage, 'completion_tokens', 0)
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


def get_client() -> ChatOpenAI:
    global _cached_client, _cached_api_base, _cached_api_key

    cfg = get_config().llm
    api_base = cfg.api_base.rstrip('/')
    api_key = cfg.api_key

    if (_cached_client is None
            or _cached_api_base != api_base
            or _cached_api_key != api_key):
        logger.info("Initializing LLM client")
        _cached_client = ChatOpenAI(
            base_url=api_base,
            api_key=api_key or "placeholder",
            model=cfg.model,
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
    logger.info(f"[chat_with_video] model={model}, video={video_path}")

    with open(video_path, 'rb') as f:
        video_base64 = base64.b64encode(f.read()).decode('utf-8')

    client = get_client()
    message = HumanMessage(content=[
        {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{video_base64}"}},
        {"type": "text", "text": prompt},
    ])

    response = client.invoke([message])
    content = response.content
    if hasattr(response, 'usage_metadata'):
        _record_token_usage(response.usage_metadata, 'chat_with_video', model)

    logger.info(f"[chat_with_video] response length={len(content)}")
    return clean_json_response(content)


def transcribe_video(video_path: str, prompt: str, model: str = '') -> str:
    """第一阶段：视频转录 - 生成 Observations"""
    logger.info(f"[transcribe_video] video={video_path}, model={model}")
    result = chat_with_video(video_path, prompt, model)
    logger.info("[transcribe_video] completed")
    return result


def generate_activity_cards(prompt: str, model: str = '') -> str:
    """第二阶段：生成活动卡片 - 基于 Observations"""
    model = model or get_config().llm.model
    logger.info(f"[generate_activity_cards] model={model}")

    response = get_client().invoke([HumanMessage(content=prompt)])
    content = response.content
    if hasattr(response, 'usage_metadata'):
        _record_token_usage(response.usage_metadata, 'generate_activity_cards', model)

    logger.info(f"[generate_activity_cards] response length={len(content)}")
    return clean_json_response(content)
