"""Read an amount of money from a customer message, in code. No model: same answer every time, instantly, free.

Understands: "KSh 2,500", "Ksh2500", "2500 bob", "2,500/=", "2.5k", and Swahili words like "elfu mbili mia tano".
Returns None if it can't find an amount. The workflow then asks the customer (it never guesses).
"""
import re


# --- digits: only numbers that are clearly MONEY (have a currency word or "k" next to them),
#     so phone numbers and order numbers are never mistaken for amounts.
MONEY_RE = re.compile(
    r"(?:\b(?:ksh|kes|sh)\.?\s*(?P<a>\d[\d,]*(?:\.\d+)?)\s*(?P<ka>k\b)?)"          # KSh 2,500 / Ksh2.5k
    r"|(?:\b(?P<b>\d[\d,]*(?:\.\d+)?)\s*(?:(?P<kb>k)\b|bob\b|shillings?\b|/=|/-))",  # 2.5k / 2500 bob / 2,500/=
    re.IGNORECASE)


# --- Swahili number words: a small, fixed vocabulary, so code can read them exactly.
UNITS = {"moja": 1, "mbili": 2, "tatu": 3, "nne": 4, "tano": 5, "sita": 6, "saba": 7, "nane": 8, "tisa": 9}
TENS = {"kumi": 10, "ishirini": 20, "thelathini": 30, "arobaini": 40, "hamsini": 50,
        "sitini": 60, "sabini": 70, "themanini": 80, "tisini": 90}



def _below_100(words: list[str], i: int) -> tuple[int, int]:
    """Read e.g. 'tano', 'kumi', 'ishirini na tano' starting at words[i]. Returns (value, next index)."""
    value = 0
    if i < len(words) and words[i] in TENS:
        value, i = TENS[words[i]], i + 1
        if i + 1 < len(words) and words[i] == "na" and words[i + 1] in UNITS:  # "ishirini na tano" = 25
            value, i = value + UNITS[words[i + 1]], i + 2
    elif i < len(words) and words[i] in UNITS:
        value, i = UNITS[words[i]], i + 1
    return value, i




def _swahili_amount(text: str) -> int | None:
    words = re.findall(r"[a-z]+", text.lower())
    if "elfu" not in words and "mia" not in words:  # no scale word: not a money amount
        return None
    total, i, started = 0, 0, False
    while i < len(words):
        w = words[i]
        if w == "elfu":                        # "elfu X" = X thousands ("elfu" alone = 1000)
            n, i = _below_100(words, i + 1)
            total += (n or 1) * 1000
            started = True
        elif w == "mia":                       # "mia X" = X hundreds
            n, i = _below_100(words, i + 1)
            total += (n or 1) * 100
            started = True
        elif started and w in TENS or started and w in UNITS:
            n, i = _below_100(words, i)
            total += n
        elif started and w == "na":            # "na" = and
            i += 1
        elif started:                          # first non-number word after the amount: stop
            break
        else:
            i += 1
    return total or None



def parse_amount(message: str) -> int | None:
    m = MONEY_RE.search(message)
    if m:
        number = m.group("a") or m.group("b")
        value = float(number.replace(",", ""))
        if m.group("ka") or m.group("kb"):
            value *= 1000
        return round(value) if value > 0 else None
    return _swahili_amount(message)



