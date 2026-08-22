import re
import unicodedata


LEGAL_FORMS = {
    "ltd": "limited",
    "ltd.": "limited",
    "p.l.c": "plc",
    "l.l.p": "llp",
}


def normalise_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s.]", " ", text)
    tokens = [LEGAL_FORMS.get(token, token.rstrip(".")) for token in text.split()]
    return " ".join(tokens)


def comparison_name(value: str) -> str:
    tokens = normalise_name(value).split()
    if tokens and tokens[-1] in {"limited", "plc", "llp"}:
        tokens.pop()
    return " ".join(tokens)


def normalise_postcode(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"\s+", "", value.upper())
    if len(compact) < 5:
        return compact
    return f"{compact[:-3]} {compact[-3:]}"

