# Normalizes and validates Israeli phone numbers for lead contacts.


def normalize_israeli_phone(phone: str) -> str | None:
    """Return an Israeli phone number in 05XXXXXXXX format, or None if invalid."""
    cleaned_phone = (
        phone.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if cleaned_phone.startswith("+9725"):
        cleaned_phone = "0" + cleaned_phone[4:]
    elif cleaned_phone.startswith("9725"):
        cleaned_phone = "0" + cleaned_phone[3:]

    if cleaned_phone.startswith("05") and len(cleaned_phone) == 10 and cleaned_phone.isdigit():
        return cleaned_phone

    return None


def validate_israeli_phone(phone: str) -> bool:
    """Return True when the phone can be normalized to a valid Israeli mobile number."""
    return normalize_israeli_phone(phone) is not None
