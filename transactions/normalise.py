"""One normalised form of a description is the key for rules and for the cache (decision 0002)."""

import re
import unicodedata

_NOT_WORD = re.compile(r"[^\w\s]+")
_SPACES = re.compile(r"\s+")


def normalise(description):
    """'  Bol.com  Purchase ' -> 'bol com purchase'. Lower case, accents removed, punctuation to spaces, single spaces."""
    text = unicodedata.normalize("NFKD", description or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = _NOT_WORD.sub(" ", text.lower())
    return _SPACES.sub(" ", text).strip()
