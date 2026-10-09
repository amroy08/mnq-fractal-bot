from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


NEW_YORK = ZoneInfo("America/New_York")

SESSION_START = time(18, 0)
SESSION_END = time(17, 0)


TIMEFRAME_HOURS = {
    "1h": 1,
    "4h": 4,
}


def get_htf_bucket_start(
    timestamp: datetime,
    higher_timeframe: str,
) -> datetime:
    if timestamp.tzinfo is None:
        raise ValueError(
            "Timestamp must include a timezone."
        )

    if higher_timeframe not in TIMEFRAME_HOURS:
        raise ValueError(
            f"Unsupported HTF boundary: {higher_timeframe}"
        )

    local_time = timestamp.astimezone(NEW_YORK)

    session_start_today = datetime.combine(
        local_time.date(),
        SESSION_START,
        tzinfo=NEW_YORK,
    )

    if local_time.time() >= SESSION_START:
        session_anchor = session_start_today
    else:
        session_anchor = session_start_today - timedelta(days=1)

    elapsed = local_time - session_anchor

    timeframe_hours = TIMEFRAME_HOURS[higher_timeframe]

    bucket_number = int(
        elapsed.total_seconds()
        // (timeframe_hours * 3600)
    )

    bucket_start = session_anchor + timedelta(
        hours=bucket_number * timeframe_hours
    )

    return bucket_start.astimezone(timestamp.tzinfo)