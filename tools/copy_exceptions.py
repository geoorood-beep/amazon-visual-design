"""Narrow copy exceptions for UTA_STYLE.md 2.7 and the forbidden-word list.

wireless and battery stay on the global forbidden list. 15-21 days stays a
duration. A hit is kept only when the image is bound to one confirmed fact
that already authorises that exact claim, and, for the duration, the same
sentence carries the full shortening caveat.
"""
import os
import re

RANGE_RE = re.compile(r"(?<!\d)15\s*[-–]\s*21\s+days\b", re.I)
CAVEAT_RE = re.compile(
    r"\bmultiple pets or (?:frequent|high-frequency) sensing may shorten runtime\b",
    re.I,
)
WORD_RE = re.compile(r"(?<![A-Za-z0-9])(wireless|battery)(?![A-Za-z0-9])", re.I)
SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]|$)")
NEGATED_CN = re.compile(r"(?:不得|不要|不能|不可|避开|不写).{0,16}(无线|电池)")


def fact_rows(text):
    """Return {id: fact, allowed, banned} from a product-card table. Banned is not a grant."""
    rows = {}
    for line in (text or "").splitlines():
        match = re.match(r"^\|\s*(F\d+)\s*\|", line)
        if not match:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        rows[cells[0]] = {
            "fact": cells[1],
            "allowed": cells[2],
            "banned": cells[3] if len(cells) > 3 else "",
        }
    return rows


def _positive_claim(fact, allowed):
    return NEGATED_CN.sub("", (fact or "") + "\n" + (allowed or ""))


def grants_from_text(text):
    """Map fact id -> set of 'wireless' | 'battery' | 'duration_15_21'."""
    grants = {}
    for fact_id, row in fact_rows(text).items():
        claim = _positive_claim(row["fact"], row["allowed"])
        allowed = row["allowed"]
        held = set()
        if "无线" in claim:
            held.add("wireless")
        if "电池" in claim:
            held.add("battery")
        if (
            re.search(r"15\s*[-–]\s*21\s*天", allowed)
            and "缩短续航" in allowed
            and "多宠" in allowed
        ):
            held.add("duration_15_21")
        grants[fact_id] = held
    return grants


def load_grants(root, product):
    path = os.path.join(root, "products", product, "PRODUCT.md")
    try:
        with open(path, encoding="utf-8") as handle:
            return grants_from_text(handle.read())
    except OSError:
        return {}


def _sentences(text):
    return [part.strip() for part in SENTENCE_RE.findall(text or "") if part.strip()]


def _sentence_at(text, index):
    for sentence in _sentences(text):
        start = text.find(sentence)
        if start <= index < start + len(sentence):
            return sentence
    return text or ""


def _is_authorised_range(text, match):
    """True when this hit is the word days inside a real 15-21 days span."""
    if match.group(0).lower() != "days":
        return False
    for range_match in RANGE_RE.finditer(text or ""):
        if range_match.end() == match.end() and range_match.start() <= match.start():
            return True
    return False


def duration_hits(text, granted):
    """Duration words that are still forbidden. granted is that fact's grant set."""
    bad = []
    allowed_span = bool(granted) and "duration_15_21" in granted
    for match in re.finditer(
        r"\b(?:day|days|week|weeks|month|months|vacation|vacations|holiday|holidays|"
        r"travel|trip|trips|weekend|weekends)\b",
        text or "",
        re.I,
    ):
        before = re.findall(r"[A-Za-z']+", (text or "")[: match.start()])[-4:]
        if any(word.lower() in {"no", "not", "without", "never", "nor"} for word in before):
            continue
        word = match.group(0)
        if allowed_span and _is_authorised_range(text, match):
            sentence = _sentence_at(text, match.start())
            if CAVEAT_RE.search(sentence) and RANGE_RE.search(sentence):
                continue
        bad.append(word)
    return bad


def term_hits(text, granted):
    """wireless/battery hits that this fact does not authorise."""
    bad = []
    for match in WORD_RE.finditer(text or ""):
        word = match.group(1).lower()
        if word in (granted or set()):
            continue
        bad.append(word)
    return bad


def line_bindings(text):
    """Yield (fact_id or '', body) for a specs lines field."""
    for part in (text or "").split(";"):
        part = part.strip()
        if not part or part.lower() == "none":
            continue
        if "|" in part:
            fact_id, body = part.split("|", 1)
            yield fact_id.strip(), body.strip()
        else:
            yield "", part
