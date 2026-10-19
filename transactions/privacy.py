"""Account numbers identify people. They are stored in full and masked in every response (decision 0005)."""


def mask_account(account_number):
    """'NLINGB1944573686' -> 'NL******3686'. The first two and last four characters stay; the length is hidden."""
    value = (account_number or "").strip()
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:2]}******{value[-4:]}"
