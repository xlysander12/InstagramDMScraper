from datetime import timedelta


def hours_minutes_seconds_from_timedelta(delta: timedelta) -> tuple[int, int, int]:
    hours = delta.total_seconds() // 3600
    minutes = delta.total_seconds() % 3600 // 60
    seconds = int(delta.total_seconds() % 60)

    return hours, minutes, seconds
