from datetime import date


def today_iso() -> str:
    return date.today().isoformat()


def validate_iso_date(d: str) -> bool:
    try:
        date.fromisoformat(d)
        return True
    except ValueError:
        return False
