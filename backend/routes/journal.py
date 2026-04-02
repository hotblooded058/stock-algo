"""
Trade Journal API Routes
"""

from fastapi import APIRouter
from src.journal.tracker import TradeJournal

router = APIRouter()
journal = TradeJournal()


@router.get("/report")
def full_report():
    """Get comprehensive trade journal analytics."""
    return journal.full_report()
