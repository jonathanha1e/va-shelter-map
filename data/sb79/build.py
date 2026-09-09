#!/usr/bin/env python3
"""
build.py — Consolidate the four California MPO "SB 79 TOD stop" datasets into a
single normalized GeoJSON (and a .js wrapper the map can load).

SB 79 (Wiener, 2025 — Gov. Code ss 65912.155-65912.162) requires every
Metropolitan Planning Organization to publish and maintain a tiered map of the
transit stops that qualify a nearby parcel for transit-oriented development.
Four MPOs together cover all seven "urban transit counties" that have qualifying
transit as of the July 1, 2026 operative date:

    SCAG   -> Los Angeles County
    MTC    -> Alameda, San Francisco, San Mateo, Santa Clara (+ Contra Costa planned)
    SANDAG -> San Diego County          (DRAFT dataset as of retrieval)
    SACOG  -> Sacramento County

Run:
    python3 build.py --fetch     # re-download the four source layers + counties
    python3 build.py             # rebuild outputs from whatever is in raw/

Outputs (written next to this script):
    sb79-tod-stops.geojson       normalized FeatureCollection, one point per source stop/access point
    sb79-tod-stops.js            `window.SB79_TOD_STOPS = <that FeatureCollection>;`
    build-report.txt             counts + anything that could not be classified

No third-party dependencies — Python 3 standard library only.
See SOURCES.md for provenance, retrieval dates, and known limitations.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

# --- source layers -----------------------------------------------------------
# Each MPO publishes an ArcGIS feature/map service. These query URLs pull every
# feature as GeoJSON in WGS84 (EPSG:4326). "portal" is the human-facing page.
SOURCES = {
    "scag": {
        "mpo": "SCAG",
        "portal": "https://scag.ca.gov/sb79",
        "service": "https://maps.scag.ca.gov/scaggis/rest/services/SB79/SB79/MapServer/0",
        "query": ("https://maps.scag.ca.gov/scaggis/rest/services/SB79/SB79/MapServer/0/query"
                  "?where=1%3D1&outFields=*&outSR=4326&f=geojson"),
    },
    "mtc": {
        "mpo": "MTC",
        "portal": "https://mtc.ca.gov/planning/land-use/senate-bill-79-regional-map",
        "service": "https://services3.arcgis.com/i2dkYWmb4wHvYPda/arcgis/rest/services/mtc_sb79_tod_stops/FeatureServer/1",
        "query": ("https://services3.arcgis.com/i2dkYWmb4wHvYPda/arcgis/rest/services/mtc_sb79_tod_stops/FeatureServer/1/query"
                  "?where=1%3D1&outFields=*&outSR=4326&f=geojson"),
    },
    "sandag": {
        "mpo": "SANDAG",
        "portal": "https://www.sandag.org/",  # DRAFT web experience id 0da0d1e879094c9cbc3724fea371c758
        "service": "https://services1.arcgis.com/HG80xaIVT1z1OdO5/arcgis/rest/services/SB79_DRAFT/FeatureServer/0",
        "query": ("https://services1.arcgis.com/HG80xaIVT1z1OdO5/arcgis/rest/services/SB79_DRAFT/FeatureServer/0/query"
                  "?where=1%3D1&outFields=*&outSR=4326&f=geojson"),
    },
    "sacog": {
        "mpo": "SACOG",
        "portal": "https://www.sacog.org/",
        "service": "https://services.sacog.org/hosting/rest/services/Transportation/SB_79_Transit_Oriented_Development_Stops/FeatureServer/0",
        "query": ("https://services.sacog.org/hosting/rest/services/Transportation/SB_79_Transit_Oriented_Development_Stops/FeatureServer/0/query"
                  "?where=1%3D1&outFields=*&outSR=4326&f=geojson"),
    },
}

COUNTIES_URL = ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/"
                "main/public/data/california-counties.geojson")

RETRIEVED = dt.date.today().isoformat()


def fetch():
    os.makedirs(RAW, exist_ok=True)
    for key, s in SOURCES.items():
        dest = os.path.join(RAW, f"{key}_stops.geojson")
        print(f"fetch {key:7s} -> {dest}")
        _download(s["query"], dest)
    dest = os.path.join(RAW, "ca-counties.geojson")
    print(f"fetch counties -> {dest}")
    _download(COUNTIES_URL, dest)


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "sb79-build/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    json.loads(data)  # validate
    with open(dest, "wb") as f:
        f.write(data)


# --- county point-in-polygon (ray casting, stdlib only) ---------------------
def _load_counties():
    with open(os.path.join(RAW, "ca-counties.geojson")) as f:
        gj = json.load(f)
    polys = []
    for feat in gj["features"]:
        name = feat["properties"]["name"]
        geom = feat["geometry"]
        rings = []
        if geom["type"] == "Polygon":
            rings = [geom["coordinates"]]
        elif geom["type"] == "MultiPolygon":
            rings = geom["coordinates"]
        for poly in rings:
            outer = poly[0]
            xs = [p[0] for p in outer]
            ys = [p[1] for p in outer]
            polys.append((name, (min(xs), min(ys), max(xs), max(ys)), poly))
    return polys


def _point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _county_for(lon, lat, polys):
    bbox_hits = []
    for name, (minx, miny, maxx, maxy), poly in polys:
        if not (minx <= lon <= maxx and miny <= lat <= maxy):
            continue
        bbox_hits.append((name, (maxx - minx) * (maxy - miny)))
        if _point_in_ring(lon, lat, poly[0]):
            if any(_point_in_ring(lon, lat, hole) for hole in poly[1:]):
                continue
            return name
    # Fallback for points just offshore / just past a county line (e.g. Muni
    # streetcar stops on the Embarcadero): take the smallest county whose
    # bounding box still contains the point.
    if bbox_hits:
        return min(bbox_hits, key=lambda t: t[1])[0]
    return None


# --- per-MPO normalizers ---------------------------------------------------
MODE = {"heavy_rail", "light_rail", "commuter_rail", "brt", "bus", "unknown"}


def _tier(v):
    s = str(v).strip().lower().replace("tier", "").strip()
    if s in ("1", "t1"):
        return 1
    if s in ("2", "t2"):
        return 2
    return None


def norm_scag(props, lon, lat):
    m = (props.get("TRN_MODE") or "").strip()
    mode = {
        "HR": "heavy_rail", "LR": "light_rail", "HR; LR": "heavy_rail",
        "BRT": "brt", "FT_BUS_LN": "bus", "CR": "commuter_rail",
    }.get(m, "unknown")
    line = (props.get("TRN_LINE") or "").strip()
    planned = (props.get("SOURCE") or "").strip() == "RTP 2024" or "Extension" in line
    src = (props.get("SOURCE") or "").strip()
    return {
        "name": (props.get("STOP_NAME") or "").strip() or None,
        "tier": _tier(props.get("SB79_TIER")),
        "mode": mode,
        "status": "planned" if planned else "existing",
        "agency": _scag_agency(m, line),
        "line": line or None,
        "city": (props.get("CITY") or "").strip() or None,
        "source_note": f"SCAG; stop source: {src}" if src and src != " " else "SCAG",
        "source_stop_id": (props.get("STOP_ID") or "").strip() or None,
    }


def _scag_agency(mode, line):
    if mode == "CR":
        return "Metrolink"
    metro_lines = {"A", "B", "C", "D", "E", "K", "G", "J"}
    head = line.split(" ")[0].split(";")[0].strip() if line else ""
    if head in metro_lines or mode in ("HR", "LR", "BRT"):
        return "LA Metro"
    return "LA Metro / municipal operator"


def norm_mtc(props, lon, lat):
    rt = str(props.get("route_type") or "").strip()
    mode = "unknown"
    if rt == "1":
        mode = "heavy_rail"
    elif rt == "2":
        mode = "commuter_rail"
    elif rt in ("0", "0, 3"):
        mode = "light_rail"
    elif rt == "3":
        mode = "bus"
    if (props.get("agency_name") or "").strip() == "AC TRANSIT" and mode == "bus":
        mode = "brt"  # AC Transit Tempo (line 1T) is branded bus rapid transit
    agency_raw = (props.get("agency_name") or "").strip()
    agency = {
        "BA": "BART", "Bay Area Rapid Transit": "BART", "BART": "BART",
        "CT": "Caltrain", "Caltrain": "Caltrain",
        "SC": "VTA", "VTA": "VTA",
        "AC TRANSIT": "AC Transit",
        "San Francisco Municipal Transportation Agency": "SFMTA / Muni",
        "Valley Link": "Valley Link",
    }.get(agency_raw, agency_raw or None)
    name = (props.get("stop_name") or "").strip()
    planned = "(Future)" in name or agency == "Valley Link"
    if agency == "Valley Link" and mode == "unknown":
        mode = "commuter_rail"
    return {
        "name": name or None,
        "tier": _tier(props.get("tod_tier")),
        "mode": mode,
        "status": "planned" if planned else "existing",
        "agency": agency,
        "line": (props.get("route_short_name") or "").strip() or None,
        "city": None,
        "source_note": "MTC (Bay Area transit operators via MTC)",
        "source_stop_id": (props.get("station_id") or props.get("stop_id") or "").strip() or None,
    }


def norm_sandag(props, lon, lat):
    st = (props.get("service_type") or "").strip()
    mode = {
        "Light Rail": "light_rail", "Bus Service": "bus",
        "Commuter Rail": "commuter_rail", "Heavy Rail": "heavy_rail",
    }.get(st, "unknown")
    uid = (props.get("stop_uid") or "").strip()
    agency = "MTS" if uid.startswith("MTS") else ("NCTD" if uid.startswith("NCTD") else None)
    if mode == "commuter_rail":
        agency = "NCTD"  # Coaster / Sprinter
    return {
        "name": (props.get("stop_name") or "").strip() or None,
        "tier": _tier(props.get("Tier")),
        "mode": mode,
        "status": "existing",
        "agency": agency,
        "line": None,
        "city": None,
        "source_note": "SANDAG (DRAFT dataset)",
        "source_stop_id": uid or None,
    }


def norm_sacog(props, lon, lat):
    t = (props.get("sb79_type") or "").strip()
    planned = t.lower().startswith("planned")
    # SACOG's published layer carries no stop name, mode, or tier. Sacramento
    # County's only qualifying existing service is SacRT light rail (no heavy
    # rail; Amtrak Capitol Corridor does not meet the >=48 trains/day
    # high-frequency-commuter-rail threshold), so existing stops are Tier 2 /
    # light rail. This is an INFERENCE, not a value from the source dataset.
    return {
        "name": None,
        "tier": None if planned else 2,
        "tier_inferred": True,
        "mode": "unknown" if planned else "light_rail",
        "mode_inferred": not planned,
        "status": "planned" if planned else "existing",
        "agency": "SacRT",
        "line": None,
        "city": None,
        "source_note": f"SACOG; source class: {t}",
        "source_stop_id": (props.get("GlobalID_1") or "").strip() or None,
    }


NORMALIZERS = {"scag": norm_scag, "mtc": norm_mtc, "sandag": norm_sandag, "sacog": norm_sacog}


def _clean_station_name(name):
    """'Heritage Square / Arroyo Station - East Entrance' -> 'heritage square / arroyo station';
    'Canoga Station (SB)' -> 'canoga station'."""
    n = name.split(" - ")[0]
    n = re.sub(r"\s*\([^)]*\)\s*$", "", n)
    n = re.sub(r"\s+(NB|SB|EB|WB|Northbound|Southbound|Eastbound|Westbound)\s*$", "", n, flags=re.I)
    return n.strip().lower()


def _station_key(mpo, sid, name, lon, lat):
    """Best-effort grouping id so consumers can collapse the several
    access-point / directional-platform rows that belong to one physical station."""
    if mpo == "MTC" and sid:
        return f"mtc:{sid}"
    if name:
        # SCAG / SANDAG ids are per-access-point; a cleaned name + coarse
        # location groups the platforms of one station far better.
        return f"{mpo.lower()}:{_clean_station_name(name)}@{round(lat, 2)},{round(lon, 2)}"
    if sid:
        return f"{mpo.lower()}:{sid}"
    return f"{mpo.lower()}:{round(lon, 4)},{round(lat, 4)}"


def build():
    polys = _load_counties()
    out_feats = []
    report = []
    per_mpo = {}
    for key, s in SOURCES.items():
        path = os.path.join(RAW, f"{key}_stops.geojson")
        with open(path) as f:
            gj = json.load(f)
        feats = gj.get("features", [])
        per_mpo[s["mpo"]] = len(feats)
        norm = NORMALIZERS[key]
        kept = 0
        for ft in feats:
            geom = ft.get("geometry")
            if not geom or geom.get("type") != "Point":
                continue
            lon, lat = geom["coordinates"][0], geom["coordinates"][1]
            props = ft.get("properties", {})
            p = norm(props, lon, lat)
            if p["tier"] is None and p["status"] == "existing" and key != "sacog":
                report.append(f"{s['mpo']}: existing stop with no tier -> {p['name']} ({props})")
            county = _county_for(lon, lat, polys)
            rec = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                "properties": {
                    "name": p["name"],
                    "station_key": _station_key(s["mpo"], p["source_stop_id"], p["name"], lon, lat),
                    "tier": p["tier"],
                    "mode": p["mode"],
                    "status": p["status"],
                    "agency": p["agency"],
                    "line": p["line"],
                    "city": p.get("city"),
                    "county": county,
                    "mpo": s["mpo"],
                    "source_dataset": s["service"],
                    "source_portal": s["portal"],
                    "source_note": p["source_note"],
                    "source_stop_id": p["source_stop_id"],
                    "retrieved": RETRIEVED,
                },
            }
            if p.get("tier_inferred"):
                rec["properties"]["tier_inferred"] = True
            if p.get("mode_inferred"):
                rec["properties"]["mode_inferred"] = True
            out_feats.append(rec)
            kept += 1
        report.append(f"{s['mpo']}: {len(feats)} source features -> {kept} points")

    fc = {
        "type": "FeatureCollection",
        "name": "sb79_tod_stops",
        "metadata": {
            "description": "Consolidated SB 79 transit-oriented-development qualifying "
                           "transit stops / access points, merged from the four California "
                           "MPO datasets that cover the urban transit counties.",
            "statutory_basis": "Cal. Gov. Code ss 65912.155-65912.162 (SB 79, Wiener, 2025); "
                               "HCD SB 79 Advisory Clarifications on Definitions (Mar 20 2026).",
            "tiers": {
                "1": "served by heavy rail transit or very-high-frequency commuter rail (>=72 trains/weekday, all directions)",
                "2": "served by light rail transit, high-frequency commuter rail (>=48 trains/weekday), or qualifying bus service (dedicated lane + <=15 min peak headways); excludes Tier 1",
            },
            "note": "SB 79 defines only Tier 1 and Tier 2. There is no 'Tier 3', and ferry "
                    "service is not a qualifying mode. Points are stop / pedestrian-access-point "
                    "level as published by each MPO; multiple points can belong to one station "
                    "(see source_stop_id / geometry proximity to deduplicate).",
            "generated": RETRIEVED,
            "generator": "data/sb79/build.py",
            "sources": {s["mpo"]: {"service": s["service"], "portal": s["portal"]} for s in SOURCES.values()},
        },
        "features": out_feats,
    }

    gj_path = os.path.join(HERE, "sb79-tod-stops.geojson")
    with open(gj_path, "w") as f:
        json.dump(fc, f, indent=1)
    js_path = os.path.join(HERE, "sb79-tod-stops.js")
    with open(js_path, "w") as f:
        f.write("/* Generated by data/sb79/build.py — do not edit by hand. See SOURCES.md. */\n")
        f.write("window.SB79_TOD_STOPS = ")
        json.dump(fc, f, separators=(",", ":"))
        f.write(";\n")

    # report
    tiers = {}
    modes = {}
    counties = {}
    stations = set()
    for ft in out_feats:
        pr = ft["properties"]
        tiers[pr["tier"]] = tiers.get(pr["tier"], 0) + 1
        modes[pr["mode"]] = modes.get(pr["mode"], 0) + 1
        counties[pr["county"]] = counties.get(pr["county"], 0) + 1
        stations.add(pr["station_key"])
    lines = []
    lines.append(f"generated {RETRIEVED}")
    lines.append(f"total points: {len(out_feats)}")
    lines.append(f"approx distinct stations (station_key): {len(stations)}")
    lines.append(f"by tier: {tiers}")
    lines.append(f"by mode: {modes}")
    lines.append(f"by county: {counties}")
    lines.append(f"by mpo (source feature counts): {per_mpo}")
    lines.append("")
    lines.append("notes / unclassified:")
    lines.extend("  " + r for r in report)
    txt = "\n".join(lines) + "\n"
    with open(os.path.join(HERE, "build-report.txt"), "w") as f:
        f.write(txt)
    print(txt)
    print(f"wrote {gj_path}")
    print(f"wrote {js_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="re-download source layers before building")
    args = ap.parse_args()
    if args.fetch:
        fetch()
    if not os.path.isdir(RAW) or not os.listdir(RAW):
        sys.exit("raw/ is empty — run: python3 build.py --fetch")
    build()
