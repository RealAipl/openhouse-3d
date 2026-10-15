# Household models V4

This supplemental release contains only actual household 3D models and their
dependent materials. It does not change any house, production website, camera,
or film workflow. Download counts refer to independent source models or explicitly
named sets, never mesh parts, material maps, or alternate formats.

The release contains **120 models**: 68 original Innerscene models, 20 new Poly
Haven models and 32 ambientCG HQ scans. This is 88 self-contained GLBs and 32
original scan ZIPs. There are zero standalone materials and zero normalized-ID
duplicates of V1–V3. During selection, 131 candidates failed the detail threshold
and ten additional assets failed visual review.

| Category | Models |
| --- | ---: |
| Furniture | 42 |
| Bedroom furniture | 19 |
| Bathroom equipment | 10 |
| Kitchen accessories | 5 |
| Appliances | 2 |
| Lamps | 5 |
| Decor | 5 |
| HQ food scans for kitchen staging | 32 |

Appliance coverage is limited to an electric stove and a vintage electric kettle.
No claim is made of a complete premium appliance collection. Source thumbnails
and source geometry were reviewed; no finished-room render was produced.

## Sources and selection

- Innerscene: original CC0 GLB models, with embedded materials and textures where
  supplied. Excludes low-poly tags, CAD-only files, irrelevant objects, demonstration
  format variants, and mirrors of other libraries. Public source pages and sitemap
  provide provenance; requests run serially with at least 3.2 seconds between
  requests. HTTP 429 causes a delay; HTTP 403 is recorded as a failure.
- ambientCG: the HQ mesh and 2K JPG textures of household food scans. Preserves
  the original source ZIP with OBJ, MTL, USD and maps. Excludes nature objects.
  The live v2 API returned mixed asset types even with a type filter, so the
  inventory checks the actual `dataType` of every record.
  The manifest credits ambientCG as the provider; an individual creator is not
  exposed in those API records. Native scan scale is preserved and must be checked
  after import; the API dimensions are not used as measurements.
- Poly Haven: 20 new original models from the official glTF 2K downloads. Source
  sizes and MD5 digests are checked, and SHA-256 is recorded for every original
  dependency. The original buffer and images are embedded into a GLB container;
  geometry, materials and transforms are preserved. Original API IDs and titles
  are normalized before comparison with V1-V3 to exclude spelling/case variants.
- V1, V2 and V3 manifests are used for provider-ID deduplication. Innerscene
  mirrors of Poly Haven and Kenney are excluded entirely; no standalone PBR
  materials are accepted. SHA-256 detects identical downloaded files within V4.
- ShareTextures is excluded: its current custom terms prohibit automated downloads
  and redistribution as a collection without written permission.
- DecorIt is excluded because the local HTTPS client reported an expired
  certificate. Certificate verification was not disabled.

The author, source page, license URL, original URL, file size, SHA-256 and measured
triangle count are recorded for each delivered item. License evidence records the
checked URLs, date, HTTP status and source-page SHA-256, with the CC0 legal text.
Provider website text is not redistributed. No CC BY or proprietary assets are included.

## Validation

`tools/household_models_v4.py` rejects incomplete downloads, HTML masquerading as
models, unexpected source checksums, external GLB dependencies, invalid buffer
bounds, invalid mesh indices, non-finite geometry and missing referenced OBJ/MTL
textures. Embedded GLB images and scan texture images are decoded. Every accepted
model has at least 10,000 triangles. Original source models are not subdivided or
otherwise inflated to meet the threshold.

Actual provider thumbnails are downloaded and decoded; the final contact sheets
are reviewed visually. Triangle count is a conservative filter, not a promise of
photorealism. A specific asset's close-up suitability still depends on its source
geometry, materials and the intended camera distance. There is no claim of a
Blender import test or a rendered furnished apartment.

The package includes `CATALOG.html`, one thumbnail per asset, contact sheets,
`MANIFEST_V4.json`, licenses, instructions and `SHA256SUMS.txt`. The final ZIP
passes a complete CRC check before publication. The published ZIP is downloaded
again and its SHA-256 compared with the local package.

## Rebuild without a runner

Install the project's normal Python dependencies, then run locally:

```powershell
python tools/household_models_v4.py --catalog docs/assets/household-v4-candidates.json --output tmp/OpenHouse_Household_Models_V4_CC0 --cache tmp/models-v4-cache
```

Use a new output directory when rebuilding. The download cache is reusable and
checked against source size/checksum metadata. Only validated downloads enter the
manifest. `rejected` records actual failures and detail-threshold exclusions; a
candidate is never counted as a delivered model. The tool does not publish releases
or start renders.

## Code checks on Windows

The repository's full test command was run in UTF-8 mode using a workspace-local
temporary directory. The pre-existing symbolic-link test cannot run because this
Windows session lacks the required symbolic-link privilege. All other 56 tests,
including eleven new asset rejection/embedding/thumbnail cases, passed. Ruff passed. No paid runner or
GPU rendering job was used.
