# Bitrix API client

import base64
import logging
from typing import Any

import httpx

from config.settings import BITRIX_WEBHOOK_URL

logger = logging.getLogger(__name__)

# Таймауты для запросов к Bitrix
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
UPLOAD_TIMEOUT = httpx.Timeout(120.0, connect=10.0)  # Больше времени для загрузки файлов


class BitrixClientError(Exception):
    """Ошибка при работе с Bitrix API."""
    pass


async def call_method(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Вызвать метод Bitrix24 REST API.
    
    Args:
        method: Название метода (например, 'tasks.task.add')
        params: Параметры запроса
        
    Returns:
        Ответ от Bitrix в виде словаря
        
    Raises:
        BitrixClientError: При ошибке запроса или ответа
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
    Загрузить файл и прикрепить к задаче.
    
    Args:
        task_id: ID задачи в Bitrix
        file_content: Содержимое файла в байтах
        file_name: Имя файла
        
    Returns:
        ID загруженного файла или None при ошибке
    """
    if not BITRIX_WEBHOOK_URL:
        raise BitrixClientError("BITRIX_WEBHOOK_URL не настроен")
    
    # Кодируем файл в base64
    file_base64 = base64.b64encode(file_content).decode('utf-8')
    
    # Загружаем файл к задаче через task.commentitem.add с файлом
    # Или используем disk.folder.uploadfile + tasks.task.files.attach
    
    # Метод 1: Добавляем комментарий с файлом к задаче
    url = f"{BITRIX_WEBHOOK_URL.rstrip('/')}/task.commentitem.add"
    
    params = {
        "TASKID": task_id,
        "FIELDS": {
            "POST_MESSAGE": f"📎 Прикреплён файл: {file_name}",
            "AUTHOR_ID": 1,  # Системный пользователь
        },
        "FILEFIELDS": {
            "UF_FORUM_MESSAGE_DOC": [
                [file_name, file_base64]
            ]
        }
    }
    
    logger.info(f"Uploading file {file_name} to task #{task_id}")
    
    try:
        async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
            response = await client.post(url, json=params)
            
            if response.status_code != 200:
                logger.error(f"File upload HTTP error: {response.status_code}")
                return None
            
            data = response.json()
            
            if "error" in data:
                logger.error(f"File upload error: {data.get('error_description', data['error'])}")
                return None
            
            file_id = data.get("result")
            logger.info(f"File uploaded successfully, comment ID: {file_id}")
            return file_id
            
    except httpx.RequestError as e:
        logger.error(f"File upload network error: {e}")
        return None
