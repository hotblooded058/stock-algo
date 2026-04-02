"""
Alerts API Routes
"""

from fastapi import APIRouter, Query
from src.alerts.notifier import get_notifier

router = APIRouter()


@router.get("/test")
def test_alerts():
    """Send a test alert to verify connectivity."""
    notifier = get_notifier()
    return notifier.test()


@router.get("/history")
def alert_history(limit: int = Query(50)):
    """Get recent alert history."""
    notifier = get_notifier()
    return {"alerts": notifier.get_history(limit)}


@router.get("/status")
def alert_status():
    """Check alert system status."""
    notifier = get_notifier()
    return {
        "telegram_enabled": notifier.telegram_enabled,
        "message": "Telegram connected" if notifier.telegram_enabled
                   else "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config/settings.py",
    }
