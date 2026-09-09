#!/usr/bin/env python3
"""
build_facilities.py — California VA medical centers + community-based outpatient
clinics (CBOCs), from the VHA's authoritative public facility dataset.

Source: "Veterans Health Administration (VHA) Facilities" hosted feature layer,
owner vhacontentmanager — per its item description, "the only authorized dataset
released for use in AGOL by the VHA for public use. Updated Monthly."
    https://services1.arcgis.com/smmmD7AGkh7eJR2a/arcgis/rest/services/Veterans_Health_Administration_(VHA)_Facilities/FeatureServer/0

We keep California facilities of these station types:
    VAMC   -> "Medical Center"
    MSCBOC -> "CBOC"   (multi-specialty CBOC)
    PCCBOC -> "CBOC"   (primary-care CBOC)
    OOS    -> "CBOC"   (other outpatient services / CRRCs) EXCEPT mobile clinics
Excluded: VTCR / MVCTR (vet centers), DRRTP (residential rehab), "* Mobile Clinic".

Outputs (next to this script):
    va-ca-facilities.geojson
    va-ca-facilities.js          window.VA_FACILITIES = <FeatureCollection>;
    facilities-verification.txt  diff of VHA coords vs the old hand-coded map

Run:  python3 build_facilities.py --fetch
"""
import argparse
import datetime as dt
import json
import math
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
SERVICE = ("https://services1.arcgis.com/smmmD7AGkh7eJR2a/arcgis/rest/services/"
           "Veterans_Health_Administration_(VHA)_Facilities/FeatureServer/0")
FIELDS = "STA_NO,STA_NAME,S_ABBR,S_ADD1,S_ADD2,S_CITY,S_STATE,S_ZIP,CNAME,LAT,LON,MONTHYEAR"

TYPE_MAP = {"VAMC": "Medical Center", "MSCBOC": "CBOC", "PCCBOC": "CBOC", "OOS": "CBOC"}
RETRIEVED = dt.date.today().isoformat()


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "va-facilities-build/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def fetch():
    os.makedirs(RAW, exist_ok=True)
    q = {"where": "S_STATE='CA'", "outFields": FIELDS, "outSR": "4326",
         "f": "json", "resultRecordCount": "2000", "returnGeometry": "true"}
    url = SERVICE + "/query?" + urllib.parse.urlencode(q)
    data = _get(url)
    with open(os.path.join(RAW, "vha_ca.json"), "w") as f:
        json.dump(data, f)
    print(f"fetched {len(data.get('features', []))} CA VHA features -> raw/vha_ca.json")


def _clean_addr(a):
    p1 = (a.get("S_ADD1") or "").strip()
    p2 = (a.get("S_ADD2") or "").strip()
    # S_ADD1 is often a building/campus name; keep it only if it has a digit
    parts = [p for p in (p1, p2) if p]
    street = p2 if (p2 and not any(c.isdigit() for c in p1)) else " ".join(parts)
    z = (a.get("S_ZIP") or "").strip()
    return f"{street}, {a.get('S_CITY','').strip()}, CA {z}".strip().strip(",")


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def build():
    data = json.load(open(os.path.join(RAW, "vha_ca.json")))
    rows = [f["attributes"] | {"_geom": f.get("geometry")} for f in data["features"]]
    vintage = rows[0]["MONTHYEAR"] if rows else "?"

    feats = []
    for a in rows:
        abbr = a["S_ABBR"]
        if abbr not in TYPE_MAP:
            continue
        name = (a["STA_NAME"] or "").strip()
        if "Mobile Clinic" in name:
            continue
        lat = a.get("LAT") or (a["_geom"] or {}).get("y")
        lon = a.get("LON") or (a["_geom"] or {}).get("x")
        if lat is None or lon is None:
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "name": name,
                "type": TYPE_MAP[abbr],
                "sta_no": a["STA_NO"],
                "sta_class": abbr,
                "address": _clean_addr(a),
                "city": (a.get("S_CITY") or "").strip(),
                "county": (a.get("CNAME") or "").strip(),
                "source": "VHA Facilities (vhacontentmanager, ArcGIS Online)",
                "source_vintage": vintage,
                "retrieved": RETRIEVED,
            },
        })
    # apply per-facility overrides (VHA public layer lags va.gov for a few sites)
    ov_path = os.path.join(HERE, "overrides.json")
    overrides = {}
    if os.path.isfile(ov_path):
        overrides = {k: v for k, v in json.load(open(ov_path)).items() if not k.startswith("_")}
    for f in feats:
        ov = overrides.get(f["properties"]["sta_no"])
        if not ov:
            continue
        if "lng" in ov and "lat" in ov:
            f["geometry"]["coordinates"] = [round(ov["lng"], 6), round(ov["lat"], 6)]
        for k in ("name", "address"):
            if k in ov:
                f["properties"][k] = ov[k]
        f["properties"]["override_reason"] = ov.get("override_reason")
        f["properties"]["override_source"] = ov.get("override_source")

    feats.sort(key=lambda f: (f["properties"]["type"] != "Medical Center", f["properties"]["name"]))

    fc = {
        "type": "FeatureCollection",
        "name": "va_ca_facilities",
        "metadata": {
            "description": "California VA medical centers and community-based outpatient "
                           "clinics (CBOCs), from the VHA's authorized public facility dataset.",
            "source_service": SERVICE,
            "source_vintage": vintage,
            "generated": RETRIEVED,
            "generator": "data/va/build_facilities.py",
            "counts": {},
        },
        "features": feats,
    }
    mc = sum(1 for f in feats if f["properties"]["type"] == "Medical Center")
    fc["metadata"]["counts"] = {"Medical Center": mc, "CBOC": len(feats) - mc, "total": len(feats)}

    with open(os.path.join(HERE, "va-ca-facilities.geojson"), "w") as f:
        json.dump(fc, f, indent=1)
    with open(os.path.join(HERE, "va-ca-facilities.js"), "w") as f:
        f.write("/* Generated by data/va/build_facilities.py — do not edit by hand. */\n")
        f.write("window.VA_FACILITIES = ")
        json.dump(fc, f, separators=(",", ":"))
        f.write(";\n")

    _verify(feats, vintage)
    print(f"wrote va-ca-facilities.geojson / .js  ({mc} medical centers, {len(feats) - mc} CBOCs)")


def _verify(feats, vintage):
    """Diff VHA coordinates against the previous hand-coded list in the old map."""
    old_path = os.path.join(HERE, "old-map-facilities.json")
    lines = [f"VHA facility coordinate verification  (VHA vintage {vintage}, checked {RETRIEVED})", ""]
    if not os.path.isfile(old_path):
        lines.append("(old-map-facilities.json not present — skipping diff)")
        open(os.path.join(HERE, "facilities-verification.txt"), "w").write("\n".join(lines) + "\n")
        return
    old = json.load(open(old_path))
    flagged = 0
    for f in feats:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        best, bestd = None, 1e9
        for o in old:
            d = haversine_m(lat, lon, o["lat"], o["lng"])
            if d < bestd:
                best, bestd = o, d
        if best is None:
            continue
        tag = "OK   " if bestd <= 150 else "MOVED"
        if bestd > 150:
            flagged += 1
        lines.append(f"{tag} {bestd:6.0f} m  {p['name'][:42]:42}  <->  {best['name'][:42]}")
    lines.append("")
    lines.append(f"{flagged} facilities differ from the old map by > 150 m "
                 f"(VHA coordinate is authoritative and is what the new map uses).")
    open(os.path.join(HERE, "facilities-verification.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    args = ap.parse_args()
    if args.fetch or not os.path.isfile(os.path.join(RAW, "vha_ca.json")):
        fetch()
    build()
