#!/usr/bin/env python3
"""
Запуск админ-панели.

Использование:
    python run_admin.py

По умолчанию запускается на http://0.0.0.0:8000
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "admin:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


