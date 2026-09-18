# California places of worship — source & method

This is the **faith-coalition layer**: sites that could host interim shelter or
safe parking on their own property under a by-right authorization (the "SB 4
for shelter" concept — SB 4, Wiener 2023, already does this for affordable
housing on faith- and college-owned land).

## Source

**HIFLD "All Places of Worship"** (Homeland Infrastructure Foundation-Level
Data), owner-published on ArcGIS Online. Per its item description, it is built
by extracting religious organizations from the **IRS Tax Exempt Organization
master file** (registered 501(c)(3)s) and geocoding their address against HERE
data.

- Service: `https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/All_Places_Of_Worship__HiFLD_Open_/FeatureServer/42`
- Retrieved **2026-09-17**, paginated 2,000 records at a time (California had
  29,833 raw records). Raw snapshot: [`raw/places_of_worship_ca.geojson`](raw/places_of_worship_ca.geojson) (9 MB).

## What this dataset is *not*

This is a **registry of organizations**, not a survey of buildings or parking
lots:

- It reflects whatever address each organization filed with the IRS. **4,761
  California records (16%) were PO-Box-only addresses with no physical
  site** — these were dropped (a PO Box can't host a tent or a car). Everything
  else still assumes the filed street address is the actual building, which
  isn't always true (some orgs use an accountant's or pastor's home address).
- Includes small home-congregations, and organizations that have since closed,
  merged, or relocated — IRS master-file updates lag real-world status.
- **Says nothing about whether a site has a parking lot, open land, or any
  physical capacity for shelter or safe parking.** That has to be verified
  site-by-site; this layer is a starting list of candidates, not a survey.
- "Tradition" (Christian/Jewish/Muslim/etc.) is inferred from the IRS NTEE
  activity code and is missing for ~63% of records — treat it as a rough hint,
  not a reliable classification.

## Output

`places-of-worship-ca.geojson` — **25,072 points** after dropping PO boxes.
Schema: `name, address, city, county, tradition`.

Unlike every other data file in this repo, **this one is not loaded via a
`<script>` tag** — at 6 MB it's far bigger than everything else combined, and
most visitors will never toggle this layer. The map `fetch()`s it lazily the
first time the "Faith-based sites" checkbox is checked, and keeps it cached
after that.

## Rebuild

```
python3 build.py --fetch
```

## Coalition-building note

If you're using this to recruit host sites, this list is a *lead list to
qualify*, not a finished target list — cross-reference with denominational
networks already organizing on this (Faith in Action / PICO California, LA
Voice, Genesis, Catholic Charities dioceses) who can tell you which of their
member congregations actually have a lot and are willing.
