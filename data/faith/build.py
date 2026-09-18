#!/usr/bin/env python3
"""
build.py — California places of worship, for the map's "faith & community
sites" layer (the SB 4 "YIGBY"-style coalition angle: interim shelter /
safe parking on faith-institution-owned land).

Source: HIFLD "All Places of Worship" — extracted from the IRS Exempt
Organization master file (registered 501(c)(3) religious organizations),
geocoded against HERE address data. This is a REGISTRY of organizations, not
a survey of buildings/parking lots — see SOURCES.md limitations.

This is the single biggest dataset on the map (~29,800 CA points), so unlike
the other layers it is NOT loaded via a blocking <script> tag. The map fetches
places-of-worship-ca.geojson on demand, the first time the layer is switched
on, and caches it after that.

Run:
    python3 build.py --fetch   # re-download all pages (paginated, 2000/page)
    python3 build.py           # rebuild from raw/

Outputs:
    places-of-worship-ca.geojson   (lean schema, no .js wrapper — fetched raw)
    build-report.txt
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
RETRIEVED = dt.date.today().isoformat()

SERVICE = ("https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/"
           "All_Places_Of_Worship__HiFLD_Open_/FeatureServer/42")
FIELDS = "NAME,STREET,CITY,ZIP,AFFILIATIO,NTEE_CD,X,Y"
PAGE = 2000
COUNTIES_URL = ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/"
                "main/public/data/california-counties.geojson")

# NTEE "X" (religion-related) subcodes -> a rough, human tradition label.
# https://nccs.urban.org/publication/irs-activity-codes -- best-effort only.
NTEE_TRADITION = {
    "X20": "Christian", "X21": "Protestant", "X22": "Christian ecumenical",
    "X30": "Jewish", "X40": "Islamic", "X50": "Buddhist", "X70": "Hindu",
    "X80": "Religious media", "X90": "Interfaith", "X99": "Religious (other/unspecified)",
}


def fetch():
    os.makedirs(RAW, exist_ok=True)
    total = _count()
    print(f"CA total per service: {total}")
    feats = []
    offset = 0
    while offset < total + PAGE:
        q = {"where": "STATE='CA'", "outFields": FIELDS, "outSR": "4326", "f": "geojson",
             "resultRecordCount": str(PAGE), "resultOffset": str(offset)}
        url = SERVICE + "/query?" + urllib.parse.urlencode(q)
        data = _get(url)
        got = data.get("features", [])
        print(f"  offset {offset}: +{len(got)}")
        if not got:
            break
        feats.extend(got)
        offset += PAGE
        time.sleep(0.2)
    json.dump({"type": "FeatureCollection", "features": feats},
               open(os.path.join(RAW, "places_of_worship_ca.geojson"), "w"))
    print(f"fetched {len(feats)} total -> raw/places_of_worship_ca.geojson")
    print("fetch ca-counties.geojson")
    open(os.path.join(RAW, "ca-counties.geojson"), "wb").write(
        urllib.request.urlopen(COUNTIES_URL, timeout=60).read())


def _count():
    url = SERVICE + "/query?" + urllib.parse.urlencode({"where": "STATE='CA'", "returnCountOnly": "true", "f": "json"})
    return _get(url)["count"]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ca-faith-build/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


# ---- county tagging: fast approximate point-in-polygon ----
def _load_counties():
    gj = json.load(open(os.path.join(RAW, "ca-counties.geojson")))
    out = []
    for feat in gj["features"]:
        name = feat["properties"]["name"]
        g = feat["geometry"]
        rings = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in rings:
            xs = [p[0] for p in poly[0]]; ys = [p[1] for p in poly[0]]
            out.append((name, (min(xs), min(ys), max(xs), max(ys)), poly[0]))
    return out


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _county(lon, lat, polys):
    candidates = [p for p in polys if p[1][0] <= lon <= p[1][2] and p[1][1] <= lat <= p[1][3]]
    for name, bbox, ring in candidates:
        if _in_ring(lon, lat, ring):
            return name
    if candidates:
        return min(candidates, key=lambda p: (p[1][2] - p[1][0]) * (p[1][3] - p[1][1]))[0]
    return None


def build():
    polys = _load_counties()
    src = json.load(open(os.path.join(RAW, "places_of_worship_ca.geojson")))
    feats = src["features"]
    out = []
    pobox_skipped = 0
    t0 = time.time()
    PO_BOX_RE = re.compile(r"^\s*P\.?\s*O\.?\s*BOX", re.I)
    for i, ft in enumerate(feats):
        p = ft["properties"]
        lon, lat = p.get("X"), p.get("Y")
        if lon is None or lat is None:
            continue
        # A PO Box has no physical lot to host shelter/parking on -- drop it.
        # These are a registry artifact (the org's mailing address), not a site.
        if PO_BOX_RE.match(p.get("STREET") or ""):
            pobox_skipped += 1
            continue
        ntee = (p.get("NTEE_CD") or "").strip()
        name = (p.get("NAME") or "").strip().title()
        addr = ", ".join(x for x in [
            (p.get("STREET") or "").strip().title(), (p.get("CITY") or "").strip().title(),
            f"CA {p.get('ZIP')}".strip()] if x and x != "CA None")
        out.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
            "properties": {
                "name": name,
                "address": addr,
                "city": (p.get("CITY") or "").strip().title() or None,
                "county": _county(lon, lat, polys),
                "tradition": NTEE_TRADITION.get(ntee[:3]),
            },
        })
        if i % 5000 == 0:
            print(f"  county-tagged {i}/{len(feats)}  ({time.time()-t0:.0f}s)")

    fc = {
        "type": "FeatureCollection", "name": "ca_places_of_worship",
        "metadata": {
            "description": "California places of worship (IRS-registered 501(c)(3) "
                           "religious organizations, HIFLD 'All Places of Worship'). "
                           "The faith-coalition / SB 4-style layer: sites that could "
                           "host interim shelter or safe parking on their own land "
                           "under a by-right authorization.",
            "source": "HIFLD All Places of Worship (IRS Exempt Organization master file, geocoded)",
            "source_service": SERVICE,
            "generated": RETRIEVED, "generator": "data/faith/build.py",
            "count": len(out),
            "pobox_excluded": pobox_skipped,
            "note": "A REGISTRY of organizations, not a survey of buildings or parking "
                    "capacity. Includes small/home congregations and may include closed "
                    "or relocated ones; does not confirm any site has land suitable for "
                    "shelter or parking. PO-Box-only addresses (no physical site) were "
                    "excluded. See SOURCES.md.",
        },
        "features": out,
    }
    json.dump(fc, open(os.path.join(HERE, "places-of-worship-ca.geojson"), "w"), separators=(",", ":"))
    rep = (f"generated {RETRIEVED}\ntotal: {len(out)}\npo_box_excluded: {pobox_skipped}\n"
           f"size_bytes: {os.path.getsize(os.path.join(HERE, 'places-of-worship-ca.geojson'))}\n")
    open(os.path.join(HERE, "build-report.txt"), "w").write(rep)
    print(rep)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        fetch()
    if not os.path.isdir(RAW) or not os.listdir(RAW):
        sys.exit("raw/ empty — run: python3 build.py --fetch")
    build()
