"""Copy checks for UTA_STYLE.md 2.7.

wireless and battery are not forbidden words. They are still facts: a product
card that never confirms 无线 cannot say wireless, and one that never confirms
电池 cannot say battery. 15-21 days stays a duration and is allowed only on the
fact whose allowed copy states it, in the same sentence as the full caveat.
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
    """Map fact id -> {'duration_15_21'} when that fact's allowed copy authorises it."""
    grants = {}
    for fact_id, row in fact_rows(text).items():
        allowed = row["allowed"]
        held = set()
        if (
            re.search(r"15\s*[-–]\s*21\s*天", allowed)
            and "缩短续航" in allowed
            and "多宠" in allowed
        ):
            held.add("duration_15_21")
        grants[fact_id] = held
    return grants


def claims_from_text(text):
    """Product-wide confirmed claims. Not a per-fact permit for a banned word."""
    claims = set()
    for row in fact_rows(text).values():
        claim = _positive_claim(row["fact"], row["allowed"])
        if "无线" in claim:
            claims.add("wireless")
        if "电池" in claim:
            claims.add("battery")
    return claims


def _read_product(root, product):
    path = os.path.join(root, "products", product, "PRODUCT.md")
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def load_grants(root, product):
    return grants_from_text(_read_product(root, product))


def load_claims(root, product):
    return claims_from_text(_read_product(root, product))


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


def invented_feature_hits(text, claims):
    """wireless/battery used by a product card that never confirms that fact."""
    bad = []
    confirmed = claims or set()
    for match in WORD_RE.finditer(text or ""):
        word = match.group(1).lower()
        if word not in confirmed:
            bad.append(word)
    return bad


COMPARISON_CAPTION_RE = re.compile(r"generic unbranded cord risk, not a test", re.I)
TIP_RE = re.compile(r"\b(tips over|tipped over|tip-over|knocked over|overturned)\b", re.I)
COMPARISON_BAN_RE = re.compile(
    r"\b(injury|injured|blood|wound|safest|guarantee|guaranteed|certified|"
    r"test report|measured test|pokpet|petlibro|oneisall|neakasa)\b",
    re.I,
)
MAX_CAPTION_WORDS = 12


def comparison_scope(product, slot, fact):
    """The only card allowed to show the generic corded risk scene."""
    return product == "pw002_s" and slot == "S6" and fact == "F8"


def comparison_problems(text):
    """Claims that the S6 risk scene must not make."""
    bad = []
    for pattern in (TIP_RE, COMPARISON_BAN_RE):
        bad.extend(match.group(0) for match in pattern.finditer(text or ""))
    return bad


def comparison_prompt_note(product, slot, fact, comparison):
    """Extra prompt sentence for the one allowed comparison card. Empty otherwise."""
    if str(comparison or "").strip().lower() != "risk_scenario":
        return ""
    if not comparison_scope(product, slot, fact):
        return ""
    return (
        "Left of frame may show one plain unbranded corded basin, not a known brand "
        "and not a copy of the main product. Two dogs may trip on that cord. "
        "The main product stays on the right with no cord. Do not tip either basin, "
        "do not show an injury, a logo, or a test instrument."
    )


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
