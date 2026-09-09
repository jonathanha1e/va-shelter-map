# SB 79 TOD transit-stop data — sources & method

This folder holds the transit-stop data behind the California VA shelter map's
SB 79 layer, plus everything needed to reproduce it.

**What SB 79 is:** the Abundant and Affordable Homes Near Transit Act (SB 79,
Wiener), signed Oct 10 2025, codified at **Cal. Government Code §§ 65912.155–
65912.162**, operative **July 1 2026**. It makes a qualifying transit-oriented
housing project an allowed use on residential / mixed-use / commercial land
within ¼ or ½ mile of a **transit-oriented development (TOD) stop**, in counties
that have one (an "urban transit county" — a county with more than 15 passenger
rail stations).

Everything downstream in the map keys off *which stops qualify and at what
tier*. That is not something to hand-estimate: the statute assigns the mapping
job to each **Metropolitan Planning Organization (MPO)**, and their maps carry a
"rebuttable presumption of validity" (§ 65912.160(f)). This dataset is a
straight consolidation of those official MPO datasets.

---

## 1. Statutory basis (what "qualifying" and "tier" mean)

Full text of the definitions section is saved at
[`raw/GOV-65912.156-text.txt`](raw/GOV-65912.156-text.txt) (retrieved 2026-09-09
from the official [California Legislative Information
site](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=65912.156)).

Key points, verbatim from § 65912.156:

| Term | Statutory definition (paraphrased; see raw text for exact wording) |
|---|---|
| **Tier 1 TOD stop** (subd. (n)) | A TOD stop in an urban transit county served by **heavy rail transit** *or* **very high frequency commuter rail** |
| **Tier 2 TOD stop** (subd. (o)) | A TOD stop in an urban transit county (that isn't Tier 1) served by **light rail transit**, **high-frequency commuter rail**, *or* **qualifying bus service** |
| **Very high frequency commuter rail** (subd. (r)) | ≥ **72 trains/day** across both directions (3-yr look-back) |
| **High-frequency commuter rail** (subd. (e)) | ≥ **48 trains/day** across both directions (3-yr look-back), below the 72 threshold |
| **Commuter rail** (subd. (b)) | Public rail transit that isn't heavy or light rail; excludes CA High-Speed Rail and Amtrak Long-Distance |
| **Heavy rail transit** (subd. (d)) | High-capacity electric railway, grade-separated, high-platform loading (e.g. BART, LA Metro B/D subway) |
| **Light rail transit** (subd. (h)) | Includes streetcar, trolley, tramway; excludes airport people movers |
| **Qualifying bus service** (subd. (o) → Pub. Res. Code § 21060.2(a)(1)) | Full-time dedicated bus lane / separate ROW **and** ≤ 15-min headways in the AM+PM peak |
| **Urban transit county** (subd. (q)) | County with **> 15 passenger rail stations** (heavy/light/commuter rail, in active service; one physical location = one station) |
| **TOD zone** (subd. (m)) | Area within ½ mile of a TOD stop |
| **Adjacent** (subd. (a)) | Within 200 ft of a pedestrian access point of a TOD stop |

### Two corrections this dataset makes to earlier versions of the map

1. **There is no "Tier 3."** § 65912.156 defines exactly two tiers — (n) Tier 1
   and (o) Tier 2. Subdivisions run (a) through (r); no third tier exists.
2. **Ferry service does not qualify.** The word "ferry" does not appear in
   § 65912.156. The qualifying modes are heavy rail, very-high / high-frequency
   commuter rail, light rail, and qualifying bus service — nothing else. A
   commuter-rail stop below the 48-trains/day threshold does **not** qualify at
   all (there is no lower tier for it to fall into).

### HCD guidance relied on by the MPOs

- **HCD, "SB 79 Advisory Clarifications on Definitions for Metropolitan Planning
  Organizations," March 20 2026.**
  <https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/sb-79-mpo-advisory.pdf>
  (copy at [`raw/hcd-sb79-advisory.txt`](raw/hcd-sb79-advisory.txt))
  Establishes: passenger-rail-station counting rule; the "Existing Rail
  Typologies" table classifying each CA rail system as heavy / light / commuter;
  and that **as of July 1 2026 the urban transit counties are Alameda, Los
  Angeles, Sacramento, San Francisco, San Mateo, Santa Clara, and San Diego.**
- **HCD letter to SCAG, June 25 2026.**
  <https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/HAU/scag-sb-79-lpa-062526.pdf>
- HCD landing page: <https://www.hcd.ca.gov/planning-and-research/sb79-tod>

### HCD "Existing Rail Typologies" table (March 2026)

| Heavy rail | Light rail | Commuter rail |
|---|---|---|
| BART (all except eBART Pittsburg Center & Antioch) · LA Metro B, D Lines | LA Metro A, C, E, K Lines · SacRT · San Diego MTS Trolley · SF Muni Metro & Streetcar · VTA Light Rail | ACE · Arrow · eBART (Pittsburg Center, Antioch) · Caltrain · Capitol Corridor · Coaster · Metrolink · Pacific Surfliner · San Joaquins (Gold Runner) · SMART · Sprinter |

(Commuter-rail lines only become TOD stops where they actually hit the 48/72
trains-per-day thresholds — see each MPO's methodology.)

---

## 2. Transit-stop datasets (the actual points)

All four MPOs whose regions contain an urban transit county have published a
tiered TOD-stop dataset. Between them they cover all seven counties. Each was
queried as GeoJSON in WGS84 on **2026-09-09** and the raw response saved under
[`raw/`](raw/).

| MPO | Counties covered | Source feature service | Portal / map | Raw file | Features |
|---|---|---|---|---|---|
| **SCAG** | Los Angeles | `https://maps.scag.ca.gov/scaggis/rest/services/SB79/SB79/MapServer/0` | <https://scag.ca.gov/sb79> | [`raw/scag_stops.geojson`](raw/scag_stops.geojson) | 406 |
| **MTC** (ABAG) | Alameda, San Francisco, San Mateo, Santa Clara (+ Contra Costa planned) | `https://services3.arcgis.com/i2dkYWmb4wHvYPda/arcgis/rest/services/mtc_sb79_tod_stops/FeatureServer/1` | <https://mtc.ca.gov/planning/land-use/senate-bill-79-regional-map> | [`raw/mtc_stops.geojson`](raw/mtc_stops.geojson) | 797 |
| **SANDAG** | San Diego | `https://services1.arcgis.com/HG80xaIVT1z1OdO5/arcgis/rest/services/SB79_DRAFT/FeatureServer/0` | SANDAG DRAFT SB 79 web experience | [`raw/sandag_stops.geojson`](raw/sandag_stops.geojson) | 182 |
| **SACOG** | Sacramento | `https://services.sacog.org/hosting/rest/services/Transportation/SB_79_Transit_Oriented_Development_Stops/FeatureServer/0` | <https://www.sacog.org/> | [`raw/sacog_stops.geojson`](raw/sacog_stops.geojson) | 200 |

Per SCAG's layer description, the MPO datasets are themselves built from **transit
agency GTFS feeds, agency GIS data, and validated station shapefiles**, then
tier-classified against the statutory criteria and HCD guidance.

Supporting reference data:

| File | What | Source |
|---|---|---|
| [`raw/ca-counties.geojson`](raw/ca-counties.geojson) | CA county polygons, used only for the `county` tag via point-in-polygon | codeforgermany/click_that_hood (public domain county boundaries) |
| [`raw/GOV-65912.156-text.txt`](raw/GOV-65912.156-text.txt) | statute definitions | leginfo.legislature.ca.gov |
| [`raw/hcd-sb79-advisory.txt`](raw/hcd-sb79-advisory.txt) | HCD advisory, text-extracted | hcd.ca.gov (PDF) |
| [`raw/scag-sb79-methodology.txt`](raw/scag-sb79-methodology.txt) | SCAG mapping methodology, text-extracted | scag.ca.gov (PDF) |

---

## 3. How the consolidated file is built

[`build.py`](build.py) (Python 3 standard library only) does:

1. **Fetch** (`--fetch`) each MPO layer + the county polygons.
2. **Normalize** every source feature to a common schema (below). Source field
   names differ per MPO; the mapping is in the `norm_*` functions.
3. **County tag** each point by ray-casting point-in-polygon against
   `ca-counties.geojson` (with a smallest-bounding-box fallback for points a few
   metres offshore, e.g. Embarcadero streetcar stops).
4. **Write** `sb79-tod-stops.geojson` (pretty), `sb79-tod-stops.js`
   (`window.SB79_TOD_STOPS = …;` for the map to load via `<script>`), and
   `build-report.txt` (counts + anything unclassified).

```
python3 build.py --fetch    # re-pull sources, then rebuild
python3 build.py            # rebuild from raw/ only
```

### Output schema (`properties` of each point)

| field | meaning |
|---|---|
| `name` | stop / station / access-point name as published (`null` for SACOG — see limitations) |
| `station_key` | best-effort id to collapse multiple access-point rows into one station |
| `tier` | `1`, `2`, or `null` |
| `mode` | `heavy_rail` · `light_rail` · `commuter_rail` · `brt` · `bus` · `unknown` |
| `status` | `existing` or `planned` |
| `agency` | operating agency (normalized) |
| `line` | route/line name(s) as published |
| `city`, `county` | `city` from SCAG only; `county` derived by point-in-polygon |
| `mpo` | `SCAG` · `MTC` · `SANDAG` · `SACOG` |
| `source_dataset` | the exact feature-service URL the point came from |
| `source_portal` | human-facing page for that MPO's map |
| `source_note` | free text, e.g. the underlying GTFS vintage where the MPO recorded it |
| `source_stop_id` | the id in the source dataset |
| `tier_inferred` / `mode_inferred` | present & `true` where this repo, not the MPO, assigned the value (SACOG only) |
| `retrieved` | date the source was pulled |

### Current build (2026-09-09)

```
total points: 1585   ·   approx distinct stations: ~1100
by tier:   Tier 2 = 1380,  Tier 1 = 186,  null = 19
by mode:   light_rail 942, bus 227, brt 177, heavy_rail 130, commuter_rail 74, unknown 35
by county: San Francisco 471, Los Angeles 406, Sacramento 200, San Diego 182,
           Santa Clara 153, Alameda 139, San Mateo 34
```

---

## 4. Known limitations — read before relying on this

- **SACOG (Sacramento) has no stop names, modes, or tiers in its published
  layer** — only "Existing TOD Stop" vs "Planned." This repo assigns existing
  SACOG stops `tier: 2` / `mode: light_rail` (Sacramento's only qualifying
  existing service is SacRT light rail; no heavy rail, and Capitol Corridor
  doesn't reach 48 trains/day). Those points are flagged `tier_inferred` /
  `mode_inferred`. Backfilling real names from the SacRT GTFS feed is a TODO.
- **SANDAG's dataset is labelled DRAFT** and every stop in it is Tier 2 (San
  Diego has no heavy rail). It includes 20 "Commuter Rail" stops marked Tier 2;
  whether Coaster/Sprinter actually clear the 48-trains/day bar is SANDAG's call
  and may change.
- **Points are stop / pedestrian-access-point level, not station level.** One
  station routinely appears as 2–8 rows (directional platforms, separate
  entrances). Use `station_key` or geometry proximity to deduplicate. This is
  intentional — SB 79 measures distance to the nearest *pedestrian access
  point*, not a station centroid.
- **MPO maps are living documents.** Tiers and inclusion change as service
  levels change, planned projects get funded, and HCD issues further guidance.
  Re-run `build.py --fetch` to refresh. `retrieved` records the vintage.
- **One MTC row** ("California St & Pierce St") carries `tod_tier: "0"` in the
  source and lands here as `tier: null`; it looks like an in-progress
  classification on MTC's side.
- **Orange County is not yet an urban transit county** and is expected to
  qualify once the OC Streetcar opens. SCAG's dataset (and therefore this file)
  covers LA County only for now.
- `county` tags come from generalized county polygons and can be wrong within a
  few metres of a county line; they are descriptive only and carry no legal
  weight.

---

## 5. Citation list

- Cal. Gov. Code §§ 65912.155–65912.162 (SB 79, Stats. 2025, Ch. 512). Text:
  <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=65912.156>
- Cal. Pub. Res. Code § 21064.3 ("major transit stop"); § 21060.2(a)(1) ("bus
  rapid transit" standard).
- HCD, SB 79 Advisory Clarifications on Definitions for MPOs (Mar 20 2026).
- HCD letter to SCAG re LPA (Jun 25 2026).
- SCAG, "SB 79 Mapping Approach and Methodology" (Jul 2 2026):
  <https://scag.ca.gov/sites/default/files/2026-07/26-417-MMI-0395-SB79-ApproachAndMethodology-Final.pdf>
- SCAG SB 79 TOD Stops & Tiers feature layer (item `c976b6aa41ce48e6a35869d1912cbace`).
- MTC/ABAG, "Senate Bill 79: Regional Map" and the `mtc_sb79_tod_stops`
  feature service (item `7906bd5706994abb833c878713d2038e`).
- SANDAG, DRAFT SB 79 Stops and Zones feature service (item
  `c82d0ef581004b2c9fd8e1c85e7321f1`).
- SACOG, SB 79 Transit-Oriented Development Stops feature service (item
  `84da298505ed4d49b31b387a7d68c4be`).
- California county boundaries: codeforgermany/click_that_hood
  `california-counties.geojson`.
