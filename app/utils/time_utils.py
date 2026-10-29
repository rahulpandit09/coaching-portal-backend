from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

# Attempt to load IANA timezone "Asia/Kolkata", with a robust fallback to fixed offset (+05:30)
# for Windows environments where tzdata may not be installed.
try:
    from zoneinfo import ZoneInfo
    try:
        IST = ZoneInfo("Asia/Kolkata")
    except Exception:
        IST = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")
except ImportError:
    IST = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")


def to_iso_ist(val):
    """
    Format a datetime object to an ISO 8601 string in IST (Indian Standard Time).
    If val is already a string or None, returns it gracefully.
    """
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=IST)
        else:
            val = val.astimezone(IST)
        return val.isoformat()
    return str(val)
