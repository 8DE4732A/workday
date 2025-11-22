import os
import base64
import re
from volcenginesdkarkruntime import Ark
from logger import get_logger
from config_manager import config

logger = get_logger(__name__)


# 缓存的 client 和对应的 API key
_cached_client = None
_cached_api_key = None


def _record_token_usage(usage, request_type: str, model: str, batch_id: int = None):
    """
    记录token使用情况

    Args:
        usage: LLM响应的usage对象
        request_type: 请求类型
        model: 模型名称
        batch_id: 批次ID（可选）
    """
    try:
        if usage and hasattr(usage, 'total_tokens'):
            from database import Database
            db = Database(config.database.path)
            db.insert_token_usage(
                request_type=request_type,
                model=model,
                prompt_tokens=getattr(usage, 'prompt_tokens', 0),
                completion_tokens=getattr(usage, 'completion_tokens', 0),
                total_tokens=usage.total_tokens,
                batch_id=batch_id
            )
            logger.debug(f"Token usage recorded: {usage.total_tokens} tokens")
    except Exception as e:
        logger.warning(f"Failed to record token usage: {e}")


def clean_json_response(content: str) -> str:
    """
    清理 LLM 响应中的 markdown 代码块标记

    如果响应是 ```json ... ``` 格式，去除代码块标记

    Args:
        content: LLM 返回的原始内容

    Returns:
        清理后的内容
    """
    content = content.strip()

    # 匹配 ```json ... ``` 或 ``` ... ``` 格式
    # 支持多种情况：```json\n{...}\n```、```\n{...}\n```
    pattern = r'^```(?:json)?\s*\n(.*?)\n```$'
    match = re.match(pattern, content, re.DOTALL)

    if match:
        cleaned = match.group(1).strip()
        logger.debug(f"[clean_json_response] Removed markdown code block markers")
        return cleaned

    return content


def get_client() -> Ark:
    """
    获取 ARK 客户端（支持动态更新 API Key）

    当 API Key 通过配置更新时，会自动创建新的客户端实例

    Returns:
        Ark 客户端实例
    """
    global _cached_client, _cached_api_key

    # 获取最新的 API Key（优先从配置读取，回退到环境变量）
    current_api_key = config.secrets.ark_api_key or os.getenv('ARK_API_KEY')

    # 如果 API Key 变化了，重新创建 client
    if _cached_client is None or _cached_api_key != current_api_key:
        logger.info(f"Initializing ARK client with {'new' if _cached_client else 'initial'} API key")
        _cached_client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=current_api_key,
        )
        _cached_api_key = current_api_key

    return _cached_client

def chat_with_video(video_path: str, prompt: str, model: str = 'ep-20251120104157-fxtrj') -> str:
    """
    使用视频和提示词调用 LLM API

    Args:
        video_path: 视频文件路径
        prompt: 提示词
        model: 模型名称

    Returns:
        LLM 返回的内容
    """
    logger.info(f"[chat_with_video] Starting LLM request - Model: {model}, Video: {video_path}")
    logger.debug(f"[chat_with_video] Prompt: {prompt[:200]}..." if len(prompt) > 200 else f"[chat_with_video] Prompt: {prompt}")

    try:
        # 读取视频文件并进行 base64 编码
        with open(video_path, 'rb') as video_file:
            video_data = video_file.read()
            video_base64 = base64.b64encode(video_data).decode('utf-8')

        logger.info(f"[chat_with_video] Video file encoded, size: {len(video_data)} bytes")

        completion = get_client().chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "video_url",
                            "video_url": {
                                "url": f'data:video/mp4;base64,{video_base64}',
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        response_content = completion.choices[0].message.content

        # 记录token使用
        _record_token_usage(completion.usage, 'chat_with_video', model)

        logger.info(f"[chat_with_video] LLM response received, length: {len(response_content)} characters")
        logger.debug(f"[chat_with_video] Response preview: {response_content[:500]}..." if len(response_content) > 500 else f"[chat_with_video] Response preview: {response_content}")
        logger.debug(f"[chat_with_video] Full response:\n{response_content}")

        # 清理 markdown 代码块标记
        cleaned_content = clean_json_response(response_content)

        return cleaned_content
    except Exception as e:
        logger.error(f"[chat_with_video] LLM request failed: {str(e)}", exc_info=True)
        raise


def transcribe_video(video_path: str, prompt: str, model: str = 'ep-20251120104157-fxtrj') -> str:
    """
    第一阶段：视频转录 - 生成 Observations

    Args:
        video_path: 视频文件路径
        prompt: 转录提示词
        model: 模型名称

    Returns:
        JSON 格式的观察记录列表
    """
    logger.info(f"[transcribe_video] Starting video transcription - Video: {video_path}, Model: {model}")
    try:
        result = chat_with_video(video_path, prompt, model)
        logger.info(f"[transcribe_video] Video transcription completed successfully")
        logger.debug(f"[transcribe_video] Transcription result:\n{result}")
        return result
    except Exception as e:
        logger.error(f"[transcribe_video] Video transcription failed: {str(e)}", exc_info=True)
        raise


def generate_activity_cards(prompt: str, model: str = 'ep-20251120104157-fxtrj') -> str:
    """
    第二阶段：生成活动卡片 - 基于 Observations

    Args:
        prompt: 卡片生成提示词（包含 observations）
        model: 模型名称

    Returns:
        JSON 格式的活动卡片列表
    """
    logger.info(f"[generate_activity_cards] Starting card generation - Model: {model}")
    logger.debug(f"[generate_activity_cards] Prompt length: {len(prompt)} characters")

    try:
        # 第二阶段不需要视频，只需要文本提示词
        completion = get_client().chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        response_content = completion.choices[0].message.content

        # 记录token使用
        _record_token_usage(completion.usage, 'generate_activity_cards', model)

        logger.info(f"[generate_activity_cards] LLM response received, length: {len(response_content)} characters")
        logger.debug(f"[generate_activity_cards] Response preview: {response_content[:500]}..." if len(response_content) > 500 else f"[generate_activity_cards] Response preview: {response_content}")
        logger.debug(f"[generate_activity_cards] Full response:\n{response_content}")

        # 清理 markdown 代码块标记
        cleaned_content = clean_json_response(response_content)

        return cleaned_content
    except Exception as e:
        logger.error(f"[generate_activity_cards] Card generation failed: {str(e)}", exc_info=True)
        raise