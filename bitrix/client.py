# Bitrix API client

import logging
from typing import Any

import httpx

from config.settings import BITRIX_WEBHOOK_URL

logger = logging.getLogger(__name__)

# Таймауты для запросов к Bitrix
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
UPLOAD_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


class BitrixClientError(Exception):
    """Ошибка при работе с Bitrix API."""
    pass


async def call_method(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Вызвать метод Bitrix24 REST API.
    """
    if not BITRIX_WEBHOOK_URL:
        raise BitrixClientError("BITRIX_WEBHOOK_URL не настроен")
    
    url = f"{BITRIX_WEBHOOK_URL.rstrip('/')}/{method}"
    
    logger.info(f"Bitrix API call: {method}")
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, json=params or {})
            
            logger.info(f"Bitrix response: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Bitrix HTTP error: {response.status_code} - {response.text[:200]}")
                raise BitrixClientError(f"HTTP {response.status_code}")
            
            data = response.json()
            
            if "error" in data:
                error_msg = data.get("error_description", data["error"])
                logger.error(f"Bitrix API error: {error_msg}")
                raise BitrixClientError(error_msg)
            
            return data
            
    except httpx.RequestError as e:
        logger.error(f"Bitrix network error: {e}")
        raise BitrixClientError(f"Ошибка сети: {e}") from e


async def upload_file_to_task(task_id: int, file_content: bytes, file_name: str) -> int | None:
    """
    Загрузить файл и прикрепить к задаче через комментарий.
    Используем multipart/form-data для загрузки.
    """
    if not BITRIX_WEBHOOK_URL:
        return None
    
    url = f"{BITRIX_WEBHOOK_URL.rstrip('/')}/task.commentitem.add"
    
    logger.info(f"Uploading file {file_name} ({len(file_content)} bytes) to task #{task_id}")
    
    try:
        # Используем form-data для загрузки файла
        files = {
            "UF_FORUM_MESSAGE_DOC": (file_name, file_content),
        }
        data = {
            "TASKID": str(task_id),
            "FIELDS[POST_MESSAGE]": f"📎 Прикреплён файл: {file_name}",
        }
        
        async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
            response = await client.post(url, data=data, files=files)
            
            logger.info(f"Upload response: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"File upload HTTP error: {response.status_code} - {response.text[:500]}")
                return None
            
            result = response.json()
            
            if "error" in result:
                logger.error(f"File upload API error: {result.get('error_description', result['error'])}")
                return None
            
            comment_id = result.get("result")
            logger.info(f"File uploaded, comment ID: {comment_id}")
            return comment_id
            
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return None
