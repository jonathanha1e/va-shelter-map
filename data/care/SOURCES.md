# California health & disability service facilities — sources & method

`care-facilities.geojson` / `.js` is the data behind the map's **"Health &
disability services"** layer group. It merges five public datasets. It does
**not** include domestic-violence facilities — those were deliberately left out
because emergency-shelter locations are confidential.

Build: `python3 build.py --fetch` (Python 3 stdlib only). Outputs the geojson,
`care-facilities.js` (`window.CARE_FACILITIES = …`), and `build-report.txt`.

## Categories & sources

| Category (`category`) | Count | Source | Query saved at |
|---|---|---|---|
| `fqhc` — Federally Qualified Health Center service delivery sites | 2,542 | **HRSA** Health Care Facilities service (`MapServer/18`, "Health Center Service Delivery Sites"), via `gisportal.hrsa.gov`. Portal: <https://data.hrsa.gov/tools/data-explorer> | [`raw/fqhc_ca.geojson`](raw/fqhc_ca.geojson) |
| `bh_substance_use` — substance-use treatment facilities | 1,209 | **SAMHSA** "Behavioral Health Treatment Facilities 2024" hosted layer (a snapshot of the FindTreatment.gov locator; `type_facility = SU`). Portal: <https://findtreatment.gov/> | [`raw/samhsa_bh_ca.geojson`](raw/samhsa_bh_ca.geojson) |
| `bh_mental_health` — mental-health treatment facilities | 654 | **SAMHSA** "National Directory of Mental Health Treatment Facilities 2024" hosted layer. Portal: <https://findtreatment.samhsa.gov/> | [`raw/samhsa_mh_ca.geojson`](raw/samhsa_mh_ca.geojson) |
| `regional_center` — DDS Regional Centers (developmental disability) | 21 | **CA DDS** regional-center locations (feature layer republished by UC Davis, ~2020 vintage). Official list: <https://www.dds.ca.gov/rc/lookup-rcs-by-county/> | [`raw/dds_rc.geojson`](raw/dds_rc.geojson) |
| `independent_living` — Independent Living Centers (disability) | 25 | **Cal OES** "CDDA Resource Centers" (the Independent Living Centers participating in the Disability Disaster Access & Resources program). | [`raw/ilc_cdda.geojson`](raw/ilc_cdda.geojson) |

All five were queried as GeoJSON in WGS84 on **2026-09-09**; the exact query URLs
are in `build.py` (`SOURCES` dict). `raw/ca-counties.geojson` (public-domain
county polygons) is used only to fill the `county` field by point-in-polygon
where the source lacks it (SAMHSA MH, Regional Centers, ILCs).

## Output schema (`properties`)

`name` · `category` · `category_label` · `address` · `city` · `county` ·
`phone` · `url` · `services` (free text — e.g. "detox, residential, outpatient"
for SU facilities, or the HRSA grant program for FQHCs) · `source` ·
`source_portal` · `retrieved`.

## Limitations

- **SAMHSA layers are 2024 snapshots** of the FindTreatment.gov / SAMHSA locator,
  republished on ArcGIS Online (FindTreatment.gov itself blocks automated
  download). Facilities open/close frequently; treat as ~1–2 years stale. To
  refresh from the primary source, pull the current locator export from SAMHSA.
- **Substance-use ≠ mental-health.** The two SAMHSA layers are separate datasets
  with some overlap; a facility offering both may appear in both.
- **Regional Centers**: the republished layer is ~2020 vintage and covers the 21
  main offices only, not the many satellite/area offices. A few headquarters may
  have relocated since — verify against dds.ca.gov before relying on one.
- **Independent Living Centers**: the Cal OES DDAR list is ~25 sites; California
  has ~28 ILC networks plus branch offices, so this is close but not the full
  set. Primary list: CA Dept of Rehabilitation / CFILC.
- **FQHC site names** occasionally carry address fragments (HRSA source quirk).
- Points are single locations as published; some organizations run multiple
  sites and each is its own row.
- `county` from generalized polygons — descriptive only, no legal weight.

## Not included (and why)

- **Domestic violence / survivor services** — emergency shelter addresses are
  confidential by law and policy (CA "Safe at Home"; HUD suppresses DV project
  geography). If added later it should be limited to public agency offices and
  Family Justice Centers, clearly labelled as not shelters.
