"""Sanskrit transliteration normalization and fuzzy matching."""

import re
import unicodedata
from difflib import SequenceMatcher

# Diacritic → normalized mapping for Sanskrit transliteration
_DIACRITIC_MAP = {
    "ā": "a",
    "ī": "i",
    "ū": "u",
    "ṛ": "ri",
    "ṝ": "ri",
    "ṭ": "t",
    "ṁ": "m",
    "ṃ": "m",
    "ḥ": "h",
    "ṣ": "sh",
    "ś": "sh",
    "ṇ": "n",
    "ṅ": "n",
    "ñ": "n",
    "ḍ": "d",
}

# Build a regex pattern from the mapping keys
_DIACRITIC_RE = re.compile("|".join(re.escape(k) for k in _DIACRITIC_MAP))


def normalize_sanskrit(text: str) -> str:
    """Normalize Sanskrit transliteration for fuzzy comparison.

    Steps: lowercase → replace diacritics → remove punctuation → collapse spaces.
    """
    text = text.lower()
    text = _DIACRITIC_RE.sub(lambda m: _DIACRITIC_MAP[m.group()], text)
    text = re.sub(r"[^a-z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _keyword_set(text: str) -> set[str]:
    """Extract keywords (words with 3+ chars) from normalized text."""
    return {w for w in text.split() if len(w) >= 3}


def score_match(query: str, candidate: str) -> float:
    """Compute combined similarity score between query and candidate.

    Score = 0.6 × sequence_score + 0.4 × keyword_score
    """
    norm_q = normalize_sanskrit(query)
    norm_c = normalize_sanskrit(candidate)

    if not norm_q or not norm_c:
        return 0.0

    # Sequence similarity
    sequence_score = SequenceMatcher(None, norm_q, norm_c).ratio()

    # Keyword overlap
    q_keywords = _keyword_set(norm_q)
    c_keywords = _keyword_set(norm_c)
    if q_keywords:
        keyword_score = len(q_keywords & c_keywords) / len(q_keywords)
    else:
        keyword_score = 0.0

    return 0.6 * sequence_score + 0.4 * keyword_score


def fuzzy_match(
    garbled: str,
    verses: list[tuple[str, str]],
    top_n: int = 3,
    threshold: float = 0.25,
) -> list[dict]:
    """Match garbled Sanskrit against a list of verse transliterations.

    Args:
        garbled: The garbled/phonetic Sanskrit text from a transcript.
        verses: List of (ref, transliteration) tuples from the database.
        top_n: Number of top matches to return (1-5).
        threshold: Minimum score to include in results.

    Returns:
        Sorted list of {"ref", "transliteration", "score"} dicts, best first.
    """
    scored = []
    for ref, transliteration in verses:
        if not transliteration:
            continue
        score = score_match(garbled, transliteration)
        if score >= threshold:
            scored.append({
                "ref": ref,
                "transliteration": transliteration,
                "score": round(score, 4),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]
