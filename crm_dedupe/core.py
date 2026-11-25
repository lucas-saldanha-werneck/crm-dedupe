"""Entity resolution for company records. Standard library only."""
import csv
import re
import unicodedata
from difflib import SequenceMatcher

LEGAL_SUFFIXES = {
    "inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation", "co",
    "company", "gmbh", "ag", "sa", "ltda", "me", "epp", "plc", "bv", "oy", "as",
    "sas", "srl", "spa", "pty", "pte",
}
FREE_MAIL = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com"}


def _ascii(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name(name):
    """Lowercase, drop accents, punctuation and legal suffixes."""
    text = _ascii(name or "").lower().replace("&", " and ")
    text = re.sub(r"(?<=\b[a-z])\.(?=[a-z]\b)", "", text)  # S.A. -> SA
    text = re.sub(r"(?<=\b[a-z])\.(?=[a-z]\.)", "", text)
    tokens = re.findall(r"[a-z0-9]+", text)
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def normalize_domain(value):
    """Reduce a URL, e-mail or bare domain to its registrable-looking host."""
    value = (value or "").strip().lower()
    if not value:
        return ""
    if "@" in value:
        value = value.split("@", 1)[1]
    value = re.sub(r"^[a-z]+://", "", value)
    value = value.split("/", 1)[0].split("?", 1)[0].split(":", 1)[0]
    if value.startswith("www."):
        value = value[4:]
    return "" if value in FREE_MAIL else value


def load_csv(path):
    """Read records; each gets a `source` column default of the file name."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for i, row in enumerate(rows):
        row.setdefault("id", str(i + 1))
        row.setdefault("source", path)
    return rows


class _UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)


def _similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def naive_duplicates(records):
    """Baseline: exact match on the raw name string. Returns clusters (lists of indexes)."""
    seen = {}
    for i, r in enumerate(records):
        seen.setdefault(r.get("name", ""), []).append(i)
    return [ix for ix in seen.values() if len(ix) > 1]


def find_duplicates(records, threshold=0.88):
    """Cluster records. Returns a list of {"members": [idx...], "reasons": [str...]}.

    Rules, strongest first:
      1. same normalized domain
      2. same normalized name AND (same country or a country is missing)
      3. fuzzy name ratio >= threshold AND (same country or a country is missing)
    """
    n = len(records)
    uf = _UnionFind(n)
    reasons = {}
    names = [normalize_name(r.get("name")) for r in records]
    domains = [normalize_domain(r.get("website") or r.get("email")) for r in records]
    countries = [(r.get("country") or "").strip().lower() for r in records]

    def compatible(i, j):
        return not countries[i] or not countries[j] or countries[i] == countries[j]

    def link(i, j, why):
        uf.union(i, j)
        reasons.setdefault((min(i, j), max(i, j)), why)

    for i in range(n):
        for j in range(i + 1, n):
            if domains[i] and domains[i] == domains[j]:
                link(i, j, "same domain")
            elif names[i] and names[i] == names[j] and compatible(i, j):
                link(i, j, "same normalized name")
            elif names[i] and names[j] and compatible(i, j):
                score = _similar(names[i], names[j])
                if score >= threshold:
                    link(i, j, f"similar name ({score:.2f})")

    groups = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)
    clusters = []
    for members in groups.values():
        if len(members) < 2:
            continue
        why = sorted({v for (a, b), v in reasons.items() if a in members and b in members})
        clusters.append({"members": members, "reasons": why})
    clusters.sort(key=lambda c: c["members"][0])
    return clusters


def report(records, clusters, baseline):
    """Markdown summary."""
    dup_rows = sum(len(c["members"]) for c in clusters)
    base_rows = sum(len(c) for c in baseline)
    lines = [
        "# Duplicate report",
        "",
        f"- Records: {len(records)}",
        f"- Clusters found: {len(clusters)} ({dup_rows} records)",
        f"- Exact-name baseline: {len(baseline)} clusters ({base_rows} records)",
        f"- Records after merge: {len(records) - dup_rows + len(clusters)}",
        "",
    ]
    for k, c in enumerate(clusters, 1):
        lines.append(f"## Cluster {k} ({'; '.join(c['reasons'])})")
        for i in c["members"]:
            r = records[i]
            lines.append(f"- [{r.get('source', '')}#{r.get('id', '')}] {r.get('name', '')} | {r.get('website', '') or r.get('email', '')} | {r.get('country', '')}")
        lines.append("")
    return "\n".join(lines)
