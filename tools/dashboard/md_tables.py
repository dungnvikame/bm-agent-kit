"""Tiny GitHub-flavoured markdown table parser (stdlib only) for README/plan tables."""
import re

_CODE = re.compile(r"`([^`]*)`")


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_tables(text):
    """Return list of tables; each table is {"headers": [...], "rows": [{header: cell}]}."""
    tables, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            headers = _cells(line)
            rows, i = [], i + 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = _cells(lines[i])
                rows.append({h: (cells[j] if j < len(cells) else "") for j, h in enumerate(headers)})
                i += 1
            tables.append({"headers": headers, "rows": rows})
        else:
            i += 1
    return tables


def strip_code(cell):
    """`name` -> name; leaves other text untouched."""
    m = _CODE.search(cell or "")
    return m.group(1) if m else (cell or "")


def strip_md(cell):
    return re.sub(r"[*`]", "", cell or "").strip()
