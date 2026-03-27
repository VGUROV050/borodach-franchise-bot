# Entry point for the Mobile API server
#
# Run alongside the Telegram bot and admin panel:
#   python run_mobile_api.py
#
# Default: 0.0.0.0:8001

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "mobile_api:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info",
    )
