# Bitrix API client

import base64
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
    Загрузить файл в Bitrix Disk и прикрепить к задаче.
    
    Шаг 1: Загружаем файл в общее хранилище
    Шаг 2: Прикрепляем к задаче через UF_TASK_WEBDAV_FILES
    """
    if not BITRIX_WEBHOOK_URL:
        return None
    
    logger.info(f"Uploading file {file_name} ({len(file_content)} bytes) to task #{task_id}")
    
    try:
        # Шаг 1: Получаем ID общего хранилища
        storage_response = await call_method("disk.storage.getlist", {
            "filter": {"ENTITY_TYPE": "common"}
        })
        
        storages = storage_response.get("result", [])
        if not storages:
            logger.error("No common storage found")
            return None
        
        storage_id = storages[0].get("ID")
        root_folder_id = storages[0].get("ROOT_OBJECT_ID")
        
        logger.info(f"Using storage {storage_id}, root folder {root_folder_id}")
        
        # Шаг 2: Загружаем файл в корневую папку хранилища
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        
        upload_url = f"{BITRIX_WEBHOOK_URL.rstrip('/')}/disk.folder.uploadfile"
        
        upload_params = {
            "id": root_folder_id,
            "data": {"NAME": file_name},
            "fileContent": [file_name, file_base64]
        }
        
        async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
            response = await client.post(upload_url, json=upload_params)
            
            if response.status_code != 200:
                logger.error(f"File upload HTTP error: {response.status_code}")
                return None
            
            result = response.json()
            logger.info(f"Disk upload result: {result}")
            
            if "error" in result:
                logger.error(f"Disk upload error: {result.get('error_description', result['error'])}")
                return None
            
            file_id = result.get("result", {}).get("ID")
            if not file_id:
                logger.error("No file ID in upload response")
                return None
            
            logger.info(f"File uploaded to disk with ID: {file_id}")
        
        # Шаг 3: Прикрепляем файл к задаче
        attach_params = {
            "taskId": task_id,
            "fileId": file_id
        }
        
        attach_response = await call_method("tasks.task.files.attach", attach_params)
        
        if attach_response.get("result"):
            logger.info(f"File {file_id} attached to task #{task_id}")
            return file_id
        else:
            logger.warning(f"File attachment result: {attach_response}")
            return file_id  # Файл загружен, но не прикреплён
            
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return None
