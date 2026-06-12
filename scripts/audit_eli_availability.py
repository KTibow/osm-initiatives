#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
from __future__ import annotations

import concurrent.futures
import io
import json
import math
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, UTC
from pathlib import Path

WATCH_IDS = {
    "Pangasinan_Bulacan_HiRes", "enedis", "eufar-balaton",
    "Nassau_Ortho_2023", "Osceola_Ortho_2022", "Osceola_Ortho_2023",
    "Saint_Lucie_Ortho_2024", "Mercer_OH_2021", "Miami_OH_2023",
    "USGS-Imagery", "King_WA_2025",
}
SOURCES = Path("vendor/editor-layer-index/sources")
OUTPUT = Path("data/eli-availability.json")
SAMPLES = 4
TIMEOUT = 8.0
WORKERS = 24
ONLY_WATCH = False
USER_AGENT = "osm-initiatives-eli-audit/0.1 (+https://github.com/KTibow/osm-initiatives)"


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2**zoom
    return max(0, min(n - 1, int((lon + 180.0) / 360.0 * n))), max(0, min(n - 1, int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)))  # fmt: skip


def coordinates(geometry: dict) -> list:
    if not geometry:
        return []
    if geometry.get("type") == "GeometryCollection":
        vals = []
        for child in geometry.get("geometries", []):
            vals.extend(coordinates(child))
        return vals
    return geometry.get("coordinates", [])


def flatten(value) -> list[tuple[float, float]]:
    if not isinstance(value, list):
        return []
    if len(value) >= 2 and all(isinstance(p, (int, float)) for p in value[:2]):
        return [(float(value[0]), float(value[1]))]
    pts = []
    for child in value:
        pts.extend(flatten(child))
    return pts


def sample_pts(points: list, count: int) -> list:
    if not points or len(points) <= count:
        return points
    return [points[round(i * (len(points) - 1) / (count - 1))] for i in range(count)]


def tile_url(template: str, zoom: int, x: int, y: int) -> str:
    import re
    url = template.replace("{zoom}", str(zoom)).replace("{z}", str(zoom)).replace("{x}", str(x)).replace("{y}", str(y)).replace("{-y}", str((2**zoom - 1) - y)).replace("{apikey}", "")
    url = re.sub(r"\{switch:([^,]+)(?:,[^}]*)*\}", r"\1", url)
    return url


def audit_url(url: str) -> dict:
    if "{" in url:
        return {"status": "bad", "detail": "unresolved template token", "url": url}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = response.read(1_500_000)
            ct = response.headers.get("Content-Type", "")
            if "text" in ct or "json" in ct or "xml" in ct or data[:1] in {b"<", b"{"}:
                return {"status": "bad", "detail": f"not_image ({ct})", "url": url}
            from PIL import Image
            Image.open(io.BytesIO(data)).convert("RGB")
            return {"status": "ok", "detail": "", "url": url}
    except urllib.error.HTTPError as e:
        return {"status": "bad", "detail": f"http_{e.code}", "url": url}
    except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
        return {"status": "bad", "detail": str(e.reason) if hasattr(e, "reason") else str(e), "url": url}
    except Exception as e:
        return {"status": "bad", "detail": str(e), "url": url}


LOG = True


def log(*args, **kw):
    if LOG:
        print(*args, file=sys.stderr, **kw)


def check_layer(layer: dict) -> dict:
    props = layer["properties"]
    lid = layer["id"]
    name = props.get("name") or lid
    cc = props.get("country_code", "")
    cat = props.get("category", "")
    typ = props.get("type", "")
    url_tmpl = props.get("url", "")
    sp = str(layer["path"])

    log(f"\n=== {lid} ===")
    log(f"  type={typ} url_template={url_tmpl[:120]}...")

    if typ != "tms" or not url_tmpl:
        log(f"  -> unsupported (type={typ}, url={bool(url_tmpl)})")
        return {"id": lid, "name": name, "countryCode": cc, "category": cat, "type": typ, "status": "unsupported", "okSamples": 0, "samples": 0, "workingZoom": None, "maxZoom": None, "exampleStatus": "", "exampleHttpStatus": "", "exampleDetail": "unsupported imagery type", "exampleUrl": "", "sourcePath": sp}

    max_z = min(int(props.get("max_zoom") or 20), 20)
    test_url = tile_url(url_tmpl, max_z, 0, 0)
    if "{" in test_url:
        log(f"  -> unsupported (unresolved tokens in URL)")
        return {"id": lid, "name": name, "countryCode": cc, "category": cat, "type": typ, "status": "unsupported", "okSamples": 0, "samples": 0, "workingZoom": None, "maxZoom": None, "exampleStatus": "", "exampleHttpStatus": "", "exampleDetail": f"unresolved template tokens: {test_url}", "exampleUrl": test_url, "sourcePath": sp}
    pts = sample_pts(flatten(coordinates(layer["geometry"])), SAMPLES)
    raw_pts = flatten(coordinates(layer["geometry"]))
    log(f"  max_zoom={max_z} raw_points={len(raw_pts)} sampled_points={len(pts)}")
    if not pts:
        log(f"  -> no geometry points, using fallback world points")
        pts = [(0, 0), (10, 10), (20, 20), (30, 30)]
    best_z = None
    best_results = None
    declared_zoom_results = None
    for z in range(max_z, max_z - 4, -1):
        if z < 5:
            break
        urls = [tile_url(url_tmpl, z, *lonlat_to_tile(lon, lat, z)) for lon, lat in pts]
        log(f"  trying zoom={z} first_url={urls[0][:150]}...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(SAMPLES, 8)) as ex:
            results = list(ex.map(audit_url, urls))
        if z == max_z:
            declared_zoom_results = results
        for idx, r in enumerate(results):
            log(f"    sample[{idx}]: status={r['status']} detail={r['detail'][:100]}")
        if any(r["status"] == "ok" for r in results):
            log(f"  -> up @z{z}")
            best_z = z
            best_results = results
            break
        best_results = results

    ok = sum(1 for r in best_results if r["status"] == "ok") if best_results else 0
    status = "up" if best_z is not None else "down"
    failing = next((r for r in best_results if r["status"] != "ok"), {}) if best_results else {}
    declared_zoom_failing = next((r for r in declared_zoom_results or [] if r["status"] != "ok"), {})
    log(f"  => {status} ok={ok}/{len(best_results)} zoom={best_z} first_fail={failing.get('detail','')[:80]}")
    return {"id": lid, "name": name, "countryCode": cc, "category": cat, "type": typ, "status": status, "okSamples": ok, "samples": len(best_results) if best_results else 0, "workingZoom": best_z, "maxZoom": max_z, "exampleStatus": failing.get("status", ""), "exampleHttpStatus": failing.get("httpStatus", ""), "exampleDetail": failing.get("detail", ""), "exampleUrl": failing.get("url", ""), "declaredZoomExampleStatus": declared_zoom_failing.get("status", ""), "declaredZoomExampleDetail": declared_zoom_failing.get("detail", ""), "declaredZoomExampleUrl": declared_zoom_failing.get("url", ""), "sourcePath": sp}


layers = []
for path in SOURCES.glob("**/*.geojson"):
    data = json.loads(path.read_text("utf-8"))
    props = data.get("properties") or {}
    lid = props.get("id") or path.stem
    if ONLY_WATCH and lid not in WATCH_IDS:
        continue
    layers.append({"id": lid, "properties": props, "geometry": data.get("geometry") or {}, "path": path})

rows = []
with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
    futures = [executor.submit(check_layer, layer) for layer in layers]
    for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
        row = future.result()
        rows.append(row)
        z = row.get("workingZoom")
        zn = f" @z{z}" if z is not None else ""
        print(f"[{i}/{len(layers)}] {row['id']} {row['status']}{zn} {row['okSamples']}/{row['samples']}", flush=True)

rows.sort(key=lambda r: (r["status"] == "up", r["id"].lower()))
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps({"generatedAt": datetime.now(UTC).isoformat(), "layers": rows}, indent=2) + "\n", "utf-8")
print(f"wrote {OUTPUT} with {len(rows)} layers")
