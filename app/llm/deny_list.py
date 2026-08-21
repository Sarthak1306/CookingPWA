import re

# Unambiguous seafood/beef/pork terms only. Deliberately excludes ambiguous
# words like "sausage" or "steak" that are commonly plant-based, chicken,
# or lamb — a false positive here blocks a legitimate suggestion, a false
# negative just means one more layer (the curated canonical_ingredient.deny_flag,
# or the person's own eyes) has to catch it. This is the hard-rule layer:
# "never seafood, beef, or pork, ever" — checked in code, not just prompted.
_DENY_TERMS = [
    # seafood
    "fish", "salmon", "tuna", "shrimp", "prawn", "crab", "lobster", "squid",
    "octopus", "mussel", "clam", "oyster", "scallop", "anchovy", "anchovies",
    "sardine", "cod", "tilapia", "trout", "mackerel", "herring", "calamari",
    "seafood", "caviar", "roe", "eel",
    # beef
    "beef", "veal", "brisket",
    # pork
    "pork", "bacon", "ham", "prosciutto", "pancetta", "chorizo", "lard",
    "pepperoni", "salami", "gammon",
]

_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _DENY_TERMS) + r")\b", re.IGNORECASE
)


def find_deny_violations(names: list[str]) -> list[str]:
    """Returns the subset of `names` that hit the deny list. Checked against
    every ingredient name in an LLM response — matched-existing or freshly
    named — regardless of what canonical_ingredient.deny_flag says, since a
    brand-new ingredient name has no deny_flag yet."""
    return [name for name in names if _PATTERN.search(name)]
