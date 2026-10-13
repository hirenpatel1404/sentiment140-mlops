"""
Text cleaning used by BOTH the training notebook and the Flask API.
Keeping it in one shared module means the model always sees text cleaned
the same way in training and in production (no training/serving skew).
"""
import html
import re

URL_RE = re.compile(r"(https?://\S+|www\.\S+)")
MENTION_RE = re.compile(r"@\w+")
REPEAT_RE = re.compile(r"(\w)\1{2,}")          # 3+ repeated letters, e.g. "sooooo"
NON_ALPHA_RE = re.compile(r"[^a-z\s]")           # anything that is not a letter or space
SPACES_RE = re.compile(r"\s+")


def clean_tweet(text: str) -> str:
    """I turn a raw tweet into clean, lowercase text."""
    if not isinstance(text, str):
        return ""
    text = html.unescape(text)                   # &amp; -> &, &quot; -> "
    text = text.lower()                          # lowercase
    text = URL_RE.sub(" ", text)                 # remove URLs
    text = MENTION_RE.sub(" ", text)             # remove @mentions
    text = text.replace("#", " ")                # keep the hashtag word, drop the # sign
    text = text.replace("'", "").replace("’", "")  # can't -> cant, so negations survive
    text = REPEAT_RE.sub(r"\1\1", text)          # sooooo -> soo
    text = NON_ALPHA_RE.sub(" ", text)           # remove numbers, emojis, punctuation
    return SPACES_RE.sub(" ", text).strip()


def tokenize(text: str) -> list:
    """I split clean text into word tokens (very short tokens are dropped)."""
    return [t for t in clean_tweet(text).split() if len(t) > 1 or t in {"i", "a"}]


def preprocess(text: str) -> str:
    """Clean + tokenize, then join back to a string for the TF-IDF vectorizer."""
    return " ".join(tokenize(text))
