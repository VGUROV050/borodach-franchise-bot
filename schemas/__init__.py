# Pydantic schemas for API validation
from .yclients import (
    YClientsCompanyInfo,
    YClientsAnalytics,
    YClientsIncomeStats,
    YClientsRecordStats,
    NetworkRatingItem,
)
from .bitrix import (
    BitrixTask,
    BitrixTaskCreate,
    BitrixTaskResult,
)

__all__ = [
    # YClients
    "YClientsCompanyInfo",
    "YClientsAnalytics",
    "YClientsIncomeStats",
    "YClientsRecordStats",
    "NetworkRatingItem",
    # Bitrix
    "BitrixTask",
    "BitrixTaskCreate",
    "BitrixTaskResult",
]

