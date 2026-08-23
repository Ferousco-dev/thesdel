"""HH:MM <-> minutes-since-midnight helpers shared by any module that does
scheduling math (litheral/study, litheral/life). Pure functions, no I/O."""


def time_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_time(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"
