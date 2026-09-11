# California VA facilities — source & method

`va-ca-facilities.geojson` / `.js` is the list of **California VA medical centers
and community-based outpatient clinics (CBOCs)** used by the map. Vet Centers are
deliberately excluded.

## Source

**"Veterans Health Administration (VHA) Facilities"** hosted feature layer on
ArcGIS Online, owner `vhacontentmanager`. Its item description states it is *"the
only authorized dataset released for use in AGOL by the VHA for public use.
Updated Monthly."*

- Service: `https://services1.arcgis.com/smmmD7AGkh7eJR2a/arcgis/rest/services/Veterans_Health_Administration_(VHA)_Facilities/FeatureServer/0`
- Raw California extract retrieved **2026-09-09**: [`raw/vha_ca.json`](raw/vha_ca.json)
- Dataset vintage in that extract: **MAR2025** (the `MONTHYEAR` field)

## What's included

Filtered to California (`S_STATE = 'CA'`) and these station classes:

| VHA class (`S_ABBR`) | Meaning | Mapped `type` |
|---|---|---|
| `VAMC` | VA medical center / hospital | `Medical Center` |
| `MSCBOC` | Multi-specialty CBOC | `CBOC` |
| `PCCBOC` | Primary-care CBOC | `CBOC` |
| `OOS` | Other outpatient services (incl. CRRCs) | `CBOC` |

Excluded: `VTCR` / `MVCTR` (Vet Centers and mobile Vet Centers), `DRRTP`
(domiciliary residential rehab — the San Diego Aspire Center), and any facility
whose name contains "Mobile Clinic".

Result: **12 medical centers, 61 CBOCs** (73 total).

## Coordinate verification

Every facility's coordinate is taken from the VHA layer (`LAT`/`LON`), which is
the authoritative source. `build_facilities.py` also diffs each against the
previous hand-coded list from `va-shelter-map017.html` and writes
[`facilities-verification.txt`](facilities-verification.txt). Most match to the
metre. Where the VHA MAR2025 vintage disagreed with the **current va.gov
location page**, an entry in [`overrides.json`](overrides.json) pins the correct
address + coordinate with a citation:

| Facility | Fix | Why |
|---|---|---|
| Antelope Valley VA Clinic | → 44439 Veterans Way, Lancaster | New clinic opened Aug 27 2025; VHA layer still lists the closed 340 E Avenue I site |
| Imperial Valley VA Clinic | → 1501 W Main St, El Centro | Current va.gov address; VHA layer lists 1115 S 4th St |
| Escondido VA Clinic | coordinate tightened to 815 E Pennsylvania Ave | matches VHA address; the old map still had the former 2010 E Valley Pkwy site |

## Rebuild

```
python3 build_facilities.py --fetch
```

Outputs `va-ca-facilities.geojson`, `va-ca-facilities.js`
(`window.VA_FACILITIES = …`), and `facilities-verification.txt`.

## Limitations

- VHA public layer vintage is MAR2025 — ~18 months old at retrieval. The three
  known-stale entries are corrected via `overrides.json`; others may exist.
- `S_ADD1` in the source is often a building/campus name rather than a street
  line; `build_facilities.py` keeps it only when it contains a digit.
- "Twenty-First Street VA Clinic" (Oakland) sits ~280 m from the main Oakland VA
  Clinic — they are genuinely separate facilities, not a duplicate.
