#!/usr/bin/env python3
"""Sync Kindle highlights from "My Clippings.txt" into content/reading/*.md.

Opt-in per book: only reading files whose front matter has a `kindle_title` param
get highlights. The value is the Kindle title without the trailing "(Author)", e.g.

  params:
    kindle_title: "The Goal: A Process of Ongoing Improvement"

A list works too, for books split across editions:

    kindle_title: ["The Obstacle Is the Way", "The Obstacle Is the Way: The Timeless Art ..."]

Highlights are written as blockquotes between marker comments, sorted by location.
Anything outside the markers is left alone. A file without markers whose body is
empty or only blockquotes is taken over whole; otherwise the block is appended.

My Clippings.txt is append-only, so extending or trimming a highlight on the Kindle
leaves the old version behind. Highlights whose location range nests with a
later-added one and whose text overlaps it are dropped as superseded edits.
Highlights deleted on the Kindle stay in the file and cannot be detected.
Notes and bookmarks are skipped.

Usage
  python3 scripts/kindle_highlights.py --dry-run   # report changes, write nothing
  python3 scripts/kindle_highlights.py             # write highlights
  python3 scripts/kindle_highlights.py --clippings ~/Downloads/My\\ Clippings.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
READING_DIR = REPO_ROOT / "content" / "reading"
DEFAULT_CLIPPINGS = Path("/Volumes/Kindle/documents/My Clippings.txt")

SEPARATOR = "=========="
START_MARKER = "<!-- kindle-highlights:start -->"
END_MARKER = "<!-- kindle-highlights:end -->"

META_RE = re.compile(r"^- Your (?P<kind>\w+)")
LOCATION_RE = re.compile(r"[Ll]ocation (?P<start>\d+)(?:-(?P<end>\d+))?")
PAGE_RE = re.compile(r"[Pp]age (?P<start>\d+)(?:-(?P<end>\d+))?")
FRONT_MATTER_RE = re.compile(r"\A---\n(?P<fm>.*?)\n---\n(?P<body>.*)\Z", re.DOTALL)
KINDLE_TITLE_RE = re.compile(r"^\s*kindle_title:\s*(?P<value>.+?)\s*$", re.MULTILINE)
TITLE_RE = re.compile(r"^title:\s*(?P<value>.+?)\s*$", re.MULTILINE)
CLIPPING_LIMIT_RE = re.compile(r"\s*<You have reached the clipping limit for this item>", re.IGNORECASE)


@dataclass(frozen=True)
class Highlight:
    title: str
    author: str
    start: int
    end: int
    order: int
    text: str

    @property
    def norm(self) -> str:
        return normalize_text(self.text)


@dataclass
class ReadingFile:
    path: Path
    title: str
    kindle_titles: list[str]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().strip(".,;:!?…\"'“”‘’ ").lower()


def normalize_title(title: str) -> str:
    title = re.sub(r"\(.*?\)", "", title.split(":")[0])
    return re.sub(r"[^\w]", "", title.lower())


def split_title_author(line: str) -> tuple[str, str]:
    line = line.replace("﻿", "").strip()
    if line.endswith(")") and " (" in line:
        idx = line.rfind(" (")
        return line[:idx].strip(), line[idx + 2 : -1].strip()
    return line, ""


def parse_range(meta: str) -> tuple[int, int] | None:
    match = LOCATION_RE.search(meta) or PAGE_RE.search(meta)
    if not match:
        return None
    start = int(match["start"])
    end_raw = match["end"]
    if not end_raw:
        return start, start
    end = int(end_raw)
    if end < start:
        # Abbreviated end like "1707-08": take the suffix digits from start.
        prefix = str(start)[: len(str(start)) - len(end_raw)]
        end = int(prefix + end_raw)
    return start, end


def parse_clippings(path: Path) -> list[Highlight]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    highlights: list[Highlight] = []
    for order, entry in enumerate(raw.split(SEPARATOR)):
        lines = entry.strip("\n").split("\n")
        if len(lines) < 3:
            continue
        meta_match = META_RE.match(lines[1].strip())
        if not meta_match or meta_match["kind"] != "Highlight":
            continue
        text = CLIPPING_LIMIT_RE.sub("", "\n".join(lines[2:])).strip()
        rng = parse_range(lines[1])
        if not text or rng is None:
            continue
        title, author = split_title_author(lines[0])
        highlights.append(Highlight(title, author, rng[0], rng[1], order, text))
    return highlights


def nested(a: Highlight, b: Highlight) -> bool:
    return (a.start <= b.start and b.end <= a.end) or (b.start <= a.start and a.end <= b.end)


def is_superseded(h: Highlight, others: list[Highlight]) -> bool:
    """True if a later-added highlight is a duplicate or an edit of this one.

    Requiring both nested ranges and overlapping text keeps short distinct
    highlights that share one coarse Kindle location.
    """
    for other in others:
        if other.order <= h.order:
            continue
        if h.norm == other.norm:
            return True
        texts_overlap = h.norm in other.norm or other.norm in h.norm
        if texts_overlap and nested(h, other):
            return True
    return False


def dedupe(highlights: list[Highlight]) -> list[Highlight]:
    kept = [h for h in highlights if not is_superseded(h, highlights)]
    return sorted(kept, key=lambda h: (h.start, h.end, h.order))


def escape_markdown(text: str) -> str:
    text = text.replace("\\", "\\\\").replace("<", "&lt;")
    text = re.sub(r"([*_`\[\]])", r"\\\1", text)
    text = re.sub(r"^(\s*)([#>+-])(\s)", r"\1\\\2\3", text, flags=re.MULTILINE)
    # "14. Even if..." would start an ordered list; escape the delimiter, not the digits.
    return re.sub(r"^(\s*\d+)([.)])(\s)", r"\1\\\2\3", text, flags=re.MULTILINE)


def render_block(highlights: list[Highlight]) -> str:
    quotes = []
    for h in highlights:
        lines = escape_markdown(h.text).split("\n")
        quotes.append("\n".join(f"> {line}".rstrip() for line in lines))
    return f"{START_MARKER}\n\n" + "\n\n".join(quotes) + f"\n\n{END_MARKER}\n"


def parse_yaml_scalar_or_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("["):
        return [str(v) for v in json.loads(value)]
    if value.startswith('"'):
        return [json.loads(value)]
    if value.startswith("'") and value.endswith("'"):
        return [value[1:-1].replace("''", "'")]
    return [value]


def load_reading_files() -> list[ReadingFile]:
    files = []
    for path in sorted(READING_DIR.glob("*.md")):
        if path.name == "_index.md":
            continue
        match = FRONT_MATTER_RE.match(path.read_text(encoding="utf-8"))
        if not match:
            continue
        fm = match["fm"]
        title_match = TITLE_RE.search(fm)
        title = parse_yaml_scalar_or_list(title_match["value"])[0] if title_match else path.stem
        kt_match = KINDLE_TITLE_RE.search(fm)
        kindle_titles = parse_yaml_scalar_or_list(kt_match["value"]) if kt_match else []
        files.append(ReadingFile(path, title, kindle_titles))
    return files


def replace_body(body: str, block: str) -> tuple[str, str]:
    if START_MARKER in body and END_MARKER in body:
        before, rest = body.split(START_MARKER, 1)
        _, after = rest.split(END_MARKER, 1)
        return before + block.rstrip("\n") + after, "replaced block"
    meaningful = [line for line in body.splitlines() if line.strip()]
    if all(line.startswith(">") for line in meaningful):
        return "\n" + block, "took over body" if meaningful else "added block"
    return body.rstrip("\n") + "\n\n" + block, "appended block (body has other content)"


def write_highlights(rf: ReadingFile, highlights: list[Highlight], dry_run: bool) -> str | None:
    text = rf.path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    assert match, rf.path
    new_body, action = replace_body(match["body"], render_block(highlights))
    new_text = f"---\n{match['fm']}\n---\n{new_body}"
    if new_text == text:
        return None
    if not dry_run:
        rf.path.write_text(new_text, encoding="utf-8")
    return action


def suggest_file(kindle_title: str, reading_files: list[ReadingFile]) -> ReadingFile | None:
    key = normalize_title(kindle_title)
    exact = [rf for rf in reading_files if normalize_title(rf.title) == key]
    if exact:
        return exact[0]
    prefix = [rf for rf in reading_files if normalize_title(rf.title) and key.startswith(normalize_title(rf.title))]
    return max(prefix, key=lambda rf: len(normalize_title(rf.title)), default=None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--clippings", type=Path, default=DEFAULT_CLIPPINGS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    clippings_path = args.clippings.expanduser()
    if not clippings_path.exists():
        print(f"Clippings file not found: {clippings_path}", file=sys.stderr)
        print("Is the Kindle plugged in? Or pass --clippings PATH.", file=sys.stderr)
        return 1

    by_title: dict[str, list[Highlight]] = {}
    for h in parse_clippings(clippings_path):
        by_title.setdefault(h.title, []).append(h)

    reading_files = load_reading_files()
    claimed: set[str] = set()

    print("Opted-in books:")
    opted_in = [rf for rf in reading_files if rf.kindle_titles]
    if not opted_in:
        print("  (none)")
    for rf in opted_in:
        missing = [t for t in rf.kindle_titles if t not in by_title]
        for title in missing:
            print(f"  WARNING {rf.path.name}: kindle_title not in clippings: {title!r}")
        raw = [h for t in rf.kindle_titles for h in by_title.get(t, [])]
        claimed.update(rf.kindle_titles)
        if not raw:
            continue
        kept = dedupe(raw)
        action = write_highlights(rf, kept, args.dry_run)
        status = action or "unchanged"
        print(f"  {rf.path.name}: {len(kept)} highlights ({len(raw) - len(kept)} superseded), {status}")

    unclaimed = sorted(
        ((t, hs) for t, hs in by_title.items() if t not in claimed),
        key=lambda item: -len(item[1]),
    )
    if unclaimed:
        print("\nKindle books not opted in (add the line to the file's params to publish):")
        for title, hs in unclaimed:
            match = suggest_file(title, reading_files)
            target = match.path.name if match else "no reading file matched"
            print(f"  {len(hs):4d}  {target}")
            print(f"        kindle_title: {json.dumps(title, ensure_ascii=False)}")

    if args.dry_run:
        print("\nDry run: nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
