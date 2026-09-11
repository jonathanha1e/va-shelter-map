#!/usr/bin/env python3
"""
build.py — California health & disability service facilities, for the map's
"care facilities" layers. Merges five public datasets into one normalized
GeoJSON (+ a .js wrapper).

Categories (map layer keys in parens):
    fqhc               (fqhc)   Federally Qualified Health Center service sites  — HRSA
    bh_substance_use   (bhSU)   Substance-use treatment facilities              — SAMHSA
    bh_mental_health   (bhMH)   Mental-health treatment facilities              — SAMHSA
    regional_center    (rc)     DDS Regional Centers (developmental disability)  — CA DDS
    independent_living (ilc)    Independent Living Centers (disability)          — Cal OES / DDAR

These are NOT domestic-violence facilities — that layer was deliberately left
out because shelter addresses are confidential.

Run:
    python3 build.py --fetch   # re-download the five sources + county polygons
    python3 build.py           # rebuild outputs from raw/

Outputs (next to this script):
    care-facilities.geojson
    care-facilities.js         window.CARE_FACILITIES = <FeatureCollection>;
    build-report.txt

Standard library only. See SOURCES.md for provenance and limitations.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
RETRIEVED = dt.date.today().isoformat()

SOURCES = {
    "fqhc_ca.geojson": {
        "label": "HRSA Health Center Program — service delivery sites",
        "portal": "https://data.hrsa.gov/tools/data-explorer",
        "query": ("https://gisportal.hrsa.gov/server/rest/services/HealthCareFacilities/HealthCareFacilities/MapServer/18/query"
                  "?where=SITE_STATE_ABBR%3D%27CA%27&outFields=SITE_NM,SITE_ADDRESS,SITE_CITY,SITE_ZIP_CD,LIST_BOX_COUNTY_NM,"
                  "SITE_PHONE_NUM,SITE_URL,HRSA_GRANT_PROG_DESC,SITE_SVC_DELIV_DESC,X,Y"
                  "&returnGeometry=true&outSR=4326&f=geojson&resultRecordCount=3000"),
    },
    "samhsa_bh_ca.geojson": {
        "label": "SAMHSA behavioral health treatment facilities 2024 — substance use",
        "portal": "https://findtreatment.gov/",
        "query": ("https://services.arcgis.com/iW55qaI4k5NTm9RB/arcgis/rest/services/Behavioral_Health_Treatment_Facilities_2024/FeatureServer/0/query"
                  "?where=state%3D%27CA%27&outFields=name1,name2,street1,city,county,zip,phone,website,type_facility,sa,dt,otp,res,op,hi"
                  "&returnGeometry=true&outSR=4326&f=geojson&resultRecordCount=3000"),
    },
    "samhsa_mh_ca.geojson": {
        "label": "SAMHSA National Directory of Mental Health Treatment Facilities 2024",
        "portal": "https://findtreatment.samhsa.gov/",
        "query": ("https://services2.arcgis.com/cPVqgcKAQtE6xCja/arcgis/rest/services/National_Directory_of_Mental_Health_Treatment_Facilities_2024/FeatureServer/20/query"
                  "?where=USER_state%3D%27CA%27&outFields=USER_name1,USER_name2,USER_street1,USER_city,USER_state,USER_zip,USER_phone,USER_service_code_info"
                  "&returnGeometry=true&outSR=4326&f=geojson&resultRecordCount=4000"),
    },
    "dds_rc.geojson": {
        "label": "California DDS Regional Center locations",
        "portal": "https://www.dds.ca.gov/rc/lookup-rcs-by-county/",
        "query": ("https://services9.arcgis.com/mt4kvYhNXSa5AqLG/arcgis/rest/services/California_DDS_regional_center_locations/FeatureServer/0/query"
                  "?where=1%3D1&outFields=*&outSR=4326&f=geojson"),
    },
    "ilc_cdda.geojson": {
        "label": "California Independent Living Centers (Cal OES / DDAR resource centers)",
        "portal": "https://www.caloes.ca.gov/office-of-the-director/operations/access-functional-needs/disability-disaster-access-resources/",
        "query": ("https://services.arcgis.com/BLN4oKB0N1YSgvY8/arcgis/rest/services/CDDA_Resource_Centers/FeatureServer/0/query"
                  "?where=1%3D1&outFields=*&outSR=4326&f=geojson"),
    },
}
COUNTIES_URL = ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/"
                "main/public/data/california-counties.geojson")

CATEGORY_LABEL = {
    "fqhc": "Federally Qualified Health Center",
    "bh_substance_use": "Substance-use treatment",
    "bh_mental_health": "Mental-health treatment",
    "regional_center": "DDS Regional Center",
    "independent_living": "Independent Living Center",
}


# ----- fetch -----
def fetch():
    os.makedirs(RAW, exist_ok=True)
    for fname, s in SOURCES.items():
        dest = os.path.join(RAW, fname)
        print(f"fetch {fname}")
        _dl(s["query"], dest)
    print("fetch ca-counties.geojson")
    _dl(COUNTIES_URL, os.path.join(RAW, "ca-counties.geojson"))


def _dl(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "ca-care-build/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    json.loads(data)
    open(dest, "wb").write(data)


# ----- county point-in-polygon -----
def _load_counties():
    gj = json.load(open(os.path.join(RAW, "ca-counties.geojson")))
    polys = []
    for feat in gj["features"]:
        name = feat["properties"]["name"]
        g = feat["geometry"]
        rings = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in rings:
            xs = [p[0] for p in poly[0]]
            ys = [p[1] for p in poly[0]]
            polys.append((name, (min(xs), min(ys), max(xs), max(ys)), poly))
    return polys


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
    hits = []
    for name, bbox, poly in polys:
        if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
            continue
        hits.append((name, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])))
        if _in_ring(lon, lat, poly[0]) and not any(_in_ring(lon, lat, h) for h in poly[1:]):
            return name
    return min(hits, key=lambda t: t[1])[0] if hits else None


# ----- normalizers -----
def _title(s):
    return ("" if s is None else str(s)).strip()


def norm_fqhc(p, lon, lat):
    return {
        "name": _title(p.get("SITE_NM")),
        "category": "fqhc",
        "address": ", ".join(x for x in [_title(p.get("SITE_ADDRESS")), _title(p.get("SITE_CITY")),
                  f"CA {_title(p.get('SITE_ZIP_CD'))}".strip()] if x),
        "city": _title(p.get("SITE_CITY")),
        "county": _title(p.get("LIST_BOX_COUNTY_NM")) or None,
        "phone": _title(p.get("SITE_PHONE_NUM")) or None,
        "url": _title(p.get("SITE_URL")) or None,
        "services": _title(p.get("HRSA_GRANT_PROG_DESC")) or None,
    }


_SU_FLAGS = [("dt", "detox"), ("res", "residential"), ("op", "outpatient"),
             ("otp", "opioid treatment program"), ("hi", "hospital inpatient")]


def norm_su(p, lon, lat):
    name = _title(p.get("name1"))
    if p.get("name2"):
        name = f"{name} — {_title(p.get('name2'))}"
    svc = [lab for f, lab in _SU_FLAGS if p.get(f) in (1, "1")]
    return {
        "name": name,
        "category": "bh_substance_use",
        "address": ", ".join(x for x in [_title(p.get("street1")), _title(p.get("city")),
                  f"CA {_title(p.get('zip'))}".strip()] if x),
        "city": _title(p.get("city")),
        "county": _title(p.get("county")) or None,
        "phone": _title(p.get("phone")) or None,
        "url": _title(p.get("website")) or None,
        "services": ", ".join(svc) or "substance-use treatment",
    }


def norm_mh(p, lon, lat):
    name = _title(p.get("USER_name1"))
    if p.get("USER_name2"):
        name = f"{name} — {_title(p.get('USER_name2'))}"
    return {
        "name": name,
        "category": "bh_mental_health",
        "address": ", ".join(x for x in [_title(p.get("USER_street1")), _title(p.get("USER_city")),
                  f"CA {_title(p.get('USER_zip'))}".strip()] if x),
        "city": _title(p.get("USER_city")),
        "county": None,
        "phone": _title(p.get("USER_phone")) or None,
        "url": None,
        "services": "mental-health treatment",
    }


def norm_rc(p, lon, lat):
    ln = _title(p.get("long_name"))
    return {
        "name": ln if "regional center" in ln.lower() else ln + " Regional Center",
        "category": "regional_center",
        "address": ", ".join(x for x in [_title(p.get("address")), _title(p.get("suite")),
                  _title(p.get("city")), f"CA {_title(p.get('zip_code'))}".strip()] if x),
        "city": _title(p.get("city")),
        "county": None,
        "phone": _title(p.get("phone_number")) or None,
        "url": _title(p.get("website")) or None,
        "services": "developmental-disability services; " + _title(p.get("geographic_type") or "office"),
    }


def norm_ilc(p, lon, lat):
    return {
        "name": _title(p.get("USER_Organization")) or _title(p.get("PlaceName")),
        "category": "independent_living",
        "address": ", ".join(x for x in [_title(p.get("USER_Street")), _title(p.get("USER_Unit")),
                  _title(p.get("USER_City")), f"CA {_title(p.get('USER_Zip'))}".strip()] if x),
        "city": _title(p.get("USER_City")),
        "county": None,
        "phone": _title(p.get("USER_Phone")) or _title(p.get("USER_CDDA_Phone")) or None,
        "url": _title(p.get("USER_URL1")) or None,
        "services": "independent-living services; counties served: "
                    + (_title(p.get("USER_Counties_Served")) or "n/a"),
    }


NORM = {
    "fqhc_ca.geojson": norm_fqhc, "samhsa_bh_ca.geojson": norm_su,
    "samhsa_mh_ca.geojson": norm_mh, "dds_rc.geojson": norm_rc, "ilc_cdda.geojson": norm_ilc,
}


def build():
    polys = _load_counties()
    out, counts, per_src = [], {}, {}
    for fname, s in SOURCES.items():
        gj = json.load(open(os.path.join(RAW, fname)))
        feats = gj.get("features", [])
        per_src[fname] = len(feats)
        norm = NORM[fname]
        for ft in feats:
            g = ft.get("geometry")
            if not g or g.get("type") != "Point":
                continue
            lon, lat = g["coordinates"][:2]
            if lon is None or lat is None or not (-125 < lon < -113 and 32 < lat < 43):
                continue
            r = norm(ft.get("properties", {}), lon, lat)
            if not r["name"]:
                continue
            if not r["county"]:
                r["county"] = _county(lon, lat, polys)
            if r["county"]:
                r["county"] = r["county"].replace(" County", "").replace(" county", "").strip()
            r["category_label"] = CATEGORY_LABEL[r["category"]]
            r["source"] = s["label"]
            r["source_portal"] = s["portal"]
            r["retrieved"] = RETRIEVED
            counts[r["category"]] = counts.get(r["category"], 0) + 1
            out.append({"type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                        "properties": r})

    fc = {"type": "FeatureCollection", "name": "ca_care_facilities",
          "metadata": {
              "description": "California health & disability service facilities "
                             "(FQHCs, SAMHSA substance-use and mental-health treatment, "
                             "DDS Regional Centers, Independent Living Centers). "
                             "Does NOT include domestic-violence facilities.",
              "generated": RETRIEVED, "generator": "data/care/build.py",
              "counts": counts,
              "sources": {f: {"label": s["label"], "portal": s["portal"]} for f, s in SOURCES.items()},
          },
          "features": out}

    json.dump(fc, open(os.path.join(HERE, "care-facilities.geojson"), "w"), indent=1)
    with open(os.path.join(HERE, "care-facilities.js"), "w") as f:
        f.write("/* Generated by data/care/build.py — do not edit by hand. See SOURCES.md. */\n")
        f.write("window.CARE_FACILITIES = ")
        json.dump(fc, f, separators=(",", ":"))
        f.write(";\n")

    rep = [f"generated {RETRIEVED}", f"total: {len(out)}", f"by category: {counts}",
           f"source feature counts: {per_src}"]
    open(os.path.join(HERE, "build-report.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        fetch()
    if not os.path.isdir(RAW) or not os.listdir(RAW):
        sys.exit("raw/ empty — run: python3 build.py --fetch")
    build()
