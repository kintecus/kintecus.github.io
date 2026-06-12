#!/usr/bin/env python3
"""Resolve lat/lon (and a street address where recoverable) for each Krakow guide
place and write them into the YAML front matter.

The Krakow recommendations (content/krakow/recs/*.md) shipped with map_url values
of mixed quality: some empty, some truncated, some Google/Apple short links. None
had usable coordinates. This script resolves coordinates with a tiered strategy,
cheapest first, and writes lat/lon back via targeted line insertion so the git diff
stays minimal (no YAML library reorders keys or strips the existing formatting).

Tiers
  1. Apple inline      maps.apple.com URLs carry coordinate=LAT,LON. No network.
  2. Coords in redirect any Google short link whose redirect contains @LAT,LON or
                       !3dLAT!4dLON (covers maps.app.goo.gl and some goo.gl links).
  3. Address + geocode goo.gl links redirect to ...?q=<street address>; decode it
                       and geocode via Nominatim.
  4. Name geocode      everything else (g.page, empty, truncated): geocode the
                       place title via Nominatim.

Confidence flags surface the handful of low-trust results for human review rather
than silently writing garbage. Run --dry-run first to see the report.

Usage
  python3 scripts/geocode_krakow.py --dry-run      # resolve + report, write nothing
  python3 scripts/geocode_krakow.py                # write coords to files missing lat:
  python3 scripts/geocode_krakow.py --only mocak   # process a single file (stem)
  python3 scripts/geocode_krakow.py --force        # re-resolve even if lat: present
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RECS_DIR = Path(__file__).resolve().parent.parent / "content" / "krakow" / "recs"

NOMINATIM_UA = (
    "kintecus-krakow-geocoder/1.0 (https://ostaps.net; ostap.senyuk@gmail.com)"
)
NOMINATIM_MIN_INTERVAL = 1.1  # seconds between calls (policy: max 1 req/sec)

# Rynek Glowny, used only for the "is this plausibly in Krakow" distance check.
KRAKOW_CENTER = (50.0614, 19.9372)
MAX_KM_FROM_CENTER = 5.0
MIN_IMPORTANCE = 0.3
GENERIC_TYPES = {
    "administrative",
    "city",
    "town",
    "suburb",
    "neighbourhood",
    "quarter",
    "village",
    "municipality",
    "county",
    "state",
    "region",
}


class GeocodeError(RuntimeError):
    """Fatal error that must stop the whole run (e.g. Nominatim rate-limited)."""


# Curated overrides for places Nominatim can't resolve from the default
# "<title>, Kraków, Poland" query (renamed venues, closed venues, dead short
# links). Keyed by filename stem. A "query" is re-geocoded; explicit "lat"/"lon"
# are used as-is. Each entry documents why it's needed.
OVERRIDES: dict[str, dict] = {
    # Title says "Yomiko" but the venue is spelled "Youmiko"; geocode its address.
    "yomiko-sushi": {"query": "Józefa 2, Kraków, Poland", "note": "renamed: Youmiko, Józefa 2"},
    # g.page link dead; geocode the cafe by its bare name (full name finds nothing).
    "fitagain-coffee-and-food": {"query": "Fitagain, Kraków", "note": "g.page dead; bare-name geocode"},
    # Truncated map_url; "Manggha" alone resolves the museum cleanly.
    "manggha-centre": {"query": "Manggha, Kraków", "note": "truncated map_url; short-name geocode"},
    # Empty map_url; the venue is an OSM-tagged restaurant resolvable by name.
    "nostra-napoletana": {"query": "Nostra Napoletana, Kraków", "note": "no map_url; name geocode"},
}


# --------------------------------------------------------------------------- #
# Front matter parsing helpers (line-oriented, no YAML library)
# --------------------------------------------------------------------------- #

def split_front_matter(lines: list[str]) -> tuple[int, int]:
    """Return (start, end) line indices of the YAML front matter delimiters.

    start/end point at the two '---' lines. Raises if not a front-matter doc.
    """
    if not lines or lines[0].strip() != "---":
        raise ValueError("no opening front-matter delimiter")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return 0, i
    raise ValueError("no closing front-matter delimiter")


def find_param_line(lines: list[str], fm_end: int, key: str) -> int | None:
    """Index of `  <key>:` within the params block (before fm_end), or None."""
    pat = re.compile(r"^(\s+)" + re.escape(key) + r":\s")
    for i in range(1, fm_end):
        if pat.match(lines[i]):
            return i
    return None


def param_indent(lines: list[str], fm_end: int) -> str:
    """Leading whitespace used for keys inside the params block (e.g. '  ')."""
    line = find_param_line(lines, fm_end, "map_url")
    if line is None:
        line = find_param_line(lines, fm_end, "category")
    if line is not None:
        return re.match(r"^(\s*)", lines[line]).group(1)
    return "  "


def read_map_url(lines: list[str], fm_end: int) -> str:
    idx = find_param_line(lines, fm_end, "map_url")
    if idx is None:
        return ""
    m = re.search(r'map_url:\s*"?(.*?)"?\s*$', lines[idx])
    return m.group(1) if m else ""


def read_title(lines: list[str], fm_end: int) -> str:
    for i in range(1, fm_end):
        m = re.match(r'^title:\s*"?(.*?)"?\s*$', lines[i])
        if m:
            return m.group(1)
    return ""


def has_coords(lines: list[str], fm_end: int) -> bool:
    return find_param_line(lines, fm_end, "lat") is not None


# --------------------------------------------------------------------------- #
# Network helpers
# --------------------------------------------------------------------------- #

def curl_redirect(url: str) -> str:
    """Return the final redirect URL for a short link (one curl hop)."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{redirect_url}",
             "-A", "Mozilla/5.0", "--max-time", "20", url],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


_last_nominatim = [0.0]


def nominatim_search(query: str) -> dict | None:
    """Geocode a freeform query via Nominatim. Rate-limited; aborts on 429/403.

    Uses curl rather than urllib: stock macOS Homebrew Python often can't find a
    CA bundle (SSL CERTIFICATE_VERIFY_FAILED), whereas curl ships its own.
    """
    wait = NOMINATIM_MIN_INTERVAL - (time.monotonic() - _last_nominatim[0])
    if wait > 0:
        time.sleep(wait)
    qs = urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
    )
    url = "https://nominatim.openstreetmap.org/search?" + qs
    try:
        proc = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-A", NOMINATIM_UA,
             "--max-time", "20", url],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        _last_nominatim[0] = time.monotonic()
        return None
    _last_nominatim[0] = time.monotonic()

    body, _, status = proc.stdout.rpartition("\n")
    if status.strip() in ("429", "403"):
        raise GeocodeError(
            f"Nominatim returned HTTP {status.strip()} (rate-limited/blocked). "
            "Aborting before any partial data is written. Wait and retry, "
            "or geocode the remaining places by hand."
        )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not data:
        return None
    top = data[0]
    imp = top.get("importance")
    return {
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top.get("display_name", ""),
        "importance": float(imp) if imp is not None else None,
        "osm_type": top.get("type", ""),
    }


# --------------------------------------------------------------------------- #
# Resolver tiers
# --------------------------------------------------------------------------- #

COORD_RE = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
AT_RE = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")


def extract_redirect_coords(redirect: str) -> tuple[float, float] | None:
    m = COORD_RE.search(redirect) or AT_RE.search(redirect)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def extract_redirect_address(redirect: str) -> str | None:
    """Pull and URL-decode the q= street address from a maps.google.com redirect.

    The q= value is '<place name>, <street>, <postcode> <city>'. Drop the leading
    place-name segment so the geocoder gets a clean address.
    """
    parsed = urllib.parse.urlparse(redirect)
    q = urllib.parse.parse_qs(parsed.query).get("q")
    if not q:
        return None
    decoded = urllib.parse.unquote_plus(q[0]).strip()
    parts = [p.strip() for p in decoded.split(",")]
    # Keep everything after the first segment if it looks like an address has a
    # street number; otherwise keep the whole string.
    if len(parts) >= 2 and re.search(r"\d", ",".join(parts[1:])):
        return ", ".join(parts[1:])
    return decoded


def resolve(stem: str, title: str, map_url: str) -> dict:
    """Return {lat, lon, address, source, notes:[...]} (lat/lon None on failure)."""
    result = {"lat": None, "lon": None, "address": "", "source": "none", "notes": []}
    map_url = (map_url or "").strip()

    # Tier 0: curated overrides for venues Nominatim can't resolve by default.
    if stem in OVERRIDES:
        ov = OVERRIDES[stem]
        note = ov.get("note", "")
        if "lat" in ov and "lon" in ov:
            result.update(lat=ov["lat"], lon=ov["lon"], source="override")
            if note:
                result["notes"].append(note)
            return result
        geo = nominatim_search(ov["query"])
        if geo:
            result.update(lat=geo["lat"], lon=geo["lon"], source="override-geocode")
            if note:
                result["notes"].append(note)
            return result
        result["notes"].append(f"override query failed: {ov['query']}")

    # Tier 1: Apple Maps inline coordinates.
    if "maps.apple.com" in map_url:
        m = re.search(r"coordinate=(-?\d+\.\d+),(-?\d+\.\d+)", map_url)
        if m:
            result.update(
                lat=float(m.group(1)), lon=float(m.group(2)), source="apple-inline"
            )
            addr = re.search(r"address=([^&]+)", map_url)
            if addr:
                result["address"] = (
                    urllib.parse.unquote(addr.group(1)).split(",")[0].strip()
                )
            return result

    is_google_short = any(
        h in map_url for h in ("goo.gl/maps", "maps.app.goo.gl")
    )

    # Tiers 2 & 3 both need the redirect.
    redirect = curl_redirect(map_url) if is_google_short else ""

    # Tier 2: coordinates embedded directly in the redirect.
    if redirect:
        coords = extract_redirect_coords(redirect)
        if coords:
            result.update(
                lat=coords[0], lon=coords[1], source="redirect-coords"
            )
            return result

    # Tier 3: street address in the redirect q= -> geocode it.
    if redirect:
        address = extract_redirect_address(redirect)
        if address:
            query = address if "krak" in address.lower() else f"{address}, Kraków, Poland"
            geo = nominatim_search(query)
            if geo:
                result.update(
                    lat=geo["lat"], lon=geo["lon"], address=address,
                    source="redirect-address+nominatim",
                    notes=_score_notes(geo),
                )
                result["_importance"] = geo["importance"]
                result["_osm_type"] = geo["osm_type"]
                return result
            result["notes"].append("redirect address found but geocode failed")

    # Tier 4: geocode by place name.
    geo = nominatim_search(f"{title}, Kraków, Poland")
    if geo:
        result.update(
            lat=geo["lat"], lon=geo["lon"], source="name-geocode",
            notes=["geocoded by NAME only - verify"] + _score_notes(geo),
        )
        result["_importance"] = geo["importance"]
        result["_osm_type"] = geo["osm_type"]
        return result

    result["notes"].append("ALL TIERS FAILED - no coordinates resolved")
    return result


def _score_notes(geo: dict) -> list[str]:
    notes = []
    if geo["importance"] is None:
        notes.append("nominatim importance missing")
    elif geo["importance"] < MIN_IMPORTANCE:
        notes.append(f"low importance {geo['importance']:.2f}")
    if geo["osm_type"] in GENERIC_TYPES:
        notes.append(f"generic result type '{geo['osm_type']}' (likely centroid)")
    return notes


# --------------------------------------------------------------------------- #
# Confidence + distance
# --------------------------------------------------------------------------- #

def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dla, dlo = la2 - la1, lo2 - lo1
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def flag_reasons(result: dict) -> list[str]:
    """Reasons a result needs human review.

    Note: Nominatim's importance score is unreliable here (its addressdetails
    responses frequently report 0.0 even for correct hits), so it is NOT a flag
    on its own - only a generic-result *type* (a centroid) is. The signals that
    matter: missing coords, implausibly far from Krakow, or name-only geocoding.
    """
    reasons = []
    if result["lat"] is None or result["lon"] is None:
        return ["no coordinates"]
    dist = haversine_km((result["lat"], result["lon"]), KRAKOW_CENTER)
    if dist > MAX_KM_FROM_CENTER:
        reasons.append(f"{dist:.1f}km from center")
    if result["source"] == "name-geocode":
        reasons.append("name-only")
    for note in result.get("notes", []):
        if "centroid" in note or "CLOSED" in note or "confirm" in note:
            reasons.append(note)
    return reasons


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #

def apply_to_file(path: Path, result: dict) -> None:
    """Insert lat/lon after map_url; replace empty address in place when recovered."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    _, fm_end = split_front_matter(lines)
    indent = param_indent(lines, fm_end)

    lat_line = f"{indent}lat: {result['lat']}\n"
    lon_line = f"{indent}lon: {result['lon']}\n"

    # Replace the existing empty address: "" in place if we recovered a real one.
    if result["address"]:
        addr_idx = find_param_line(lines, fm_end, "address")
        if addr_idx is not None:
            existing = re.search(r'address:\s*"?(.*?)"?\s*$', lines[addr_idx])
            if existing and not existing.group(1).strip():
                escaped = result["address"].replace('"', '\\"')
                lines[addr_idx] = f'{indent}address: "{escaped}"\n'

    # Insert lat/lon after the map_url line (recompute indices after any edit above).
    _, fm_end = split_front_matter(lines)
    map_idx = find_param_line(lines, fm_end, "map_url")
    insert_at = (map_idx + 1) if map_idx is not None else fm_end
    lines[insert_at:insert_at] = [lat_line, lon_line]

    # Safety: never end up with more than one address: key.
    _, fm_end2 = split_front_matter(lines)
    addr_count = sum(
        1 for i in range(1, fm_end2) if re.match(r"^\s+address:\s", lines[i])
    )
    if addr_count > 1:
        raise GeocodeError(
            f"{path.name}: would produce {addr_count} address: keys; aborting"
        )

    path.write_text("".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def iter_files(only: str | None) -> list[Path]:
    files = []
    for path in sorted(RECS_DIR.glob("*.md")):
        if path.name == "_index.md":
            continue
        if only and path.stem != only:
            continue
        files.append(path)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description="Geocode Krakow guide places.")
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve and report; write nothing")
    ap.add_argument("--only", metavar="STEM",
                    help="process only this file stem (e.g. mocak)")
    ap.add_argument("--force", action="store_true",
                    help="re-resolve even if lat: is already present")
    args = ap.parse_args()

    files = iter_files(args.only)
    if not files:
        print("No matching files.", file=sys.stderr)
        return 1

    ok: list[str] = []
    flagged: list[str] = []
    skipped = 0

    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        try:
            _, fm_end = split_front_matter(lines)
        except ValueError:
            print(f"[skip] {path.name}: no front matter")
            continue

        map_url = read_map_url(lines, fm_end)
        if find_param_line(lines, fm_end, "map_url") is None:
            print(f"[skip] {path.name}: no map_url param")
            continue

        if has_coords(lines, fm_end) and not args.force:
            skipped += 1
            continue

        title = read_title(lines, fm_end)
        result = resolve(path.stem, title, map_url)
        reasons = flag_reasons(result)

        if result["lat"] is None:
            line = f"[FLAG] {path.name:<44} <none>          reason={'; '.join(reasons)}"
            flagged.append(line)
            print(line)
            continue

        dist = haversine_km((result["lat"], result["lon"]), KRAKOW_CENTER)
        coord_str = f"{result['lat']:.5f},{result['lon']:.5f}"
        tag = "FLAG" if reasons else "ok "
        line = (
            f"[{tag}] {path.name:<44} {coord_str}  ({dist:.1f}km)  "
            f"src={result['source']}"
        )
        if reasons:
            line += f"  reason={'; '.join(reasons)}"
            flagged.append(line)
        else:
            ok.append(line)
        print(line)

        if not args.dry_run:
            apply_to_file(path, result)

    print()
    print("=" * 72)
    mode = "DRY RUN (nothing written)" if args.dry_run else "WROTE coordinates"
    print(f"{mode}: {len(ok)} ok, {len(flagged)} flagged, {skipped} skipped "
          f"(already had coords)")
    if flagged:
        print("\nReview these:")
        for line in flagged:
            print("  " + line)
        print("\nFix the source map_url and re-run with --only <stem> --force, "
              "or hand-edit lat/lon.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except GeocodeError as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        sys.exit(2)
