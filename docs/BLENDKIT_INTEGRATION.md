# Blendkit (BlenderKit) — integration status and licensing

## Integrated source
- Upstream official source: https://github.com/BlenderKit/Blendkit
- Git submodule: `vendor/Blendkit`, pinned to `f4d16f767fc9a54cde843bf720741b8090df85c0`.
- Git dependencies: `bk_client` and `bk_proxor` are nested submodules.
- Licensing of addon code: GPL-2.0-or-later; model licences are SEPARATE.
- `actions/checkout@v4` with `submodules: recursive` gets the complete addon source in cloud.
- GitHub Actions `blendkit-build.yml` packages official addon into `blenderkit.zip`.

## Actual model access: IMPORTANT
The public API `https://www.blendkit.com/api/v1/search/` replied HTTP 403 from the GitHub Actions hosted runner for limited anonymous queries. No Blendkit furniture files have yet been acquired. Do not describe the placeholder/procedural furniture as downloaded Blendkit models.

Legitimate approach: find a **free** model through the official Blendkit interface (or authorized client), download its `.blend` through that interface and retain its URL, author, licence and source asset ID. Store downloaded files OUTSIDE the public Git repository and supply them to the headless renderer via an authorized private artifact/storage path.

A raw GLB or public 3D asset pack may NOT contain a Royalty Free model extractable from its host scene. CC0 is preferable when GLB distribution is needed. Royalty Free models can be used in finished video/renders in accordance with Blendkit terms.

## Blender importer in this repo
`houses/blizniak_dwulokalowy/import_blendkit_models.py`

It validates `asset_base_id`, `is_free`, `license`, official source URL, path, optional SHA256 and permitted use, imports actual Blender meshes from a properly downloaded `.blend`, scales and positions them, packs textures, and saves an edited `.blend` and provenance report.

Example private manifest (NOT a list of downloaded assets):
```json
[
  {
    "asset_base_id": "REPLACE_WITH_OFFICIAL_ID",
    "name": "Verified free sofa",
    "is_free": true,
    "license": "cc_zero",
    "source_url": "https://www.blendkit.com/asset-gallery-detail/REPLACE_WITH_OFFICIAL_ID/",
    "file": "sofa_from_official_blendkit.blend",
    "room": "A_upper_5",
    "kind": "sofa",
    "location_m": [-4.55, 1.72, 2.93],
    "rotation_z_degrees": 0,
    "width_m": 2.2,
    "sha256": "REPLACE_WITH_REAL_SHA256_OR_REMOVE_FIELD"
  }
]
```

Execute on the existing OpenHouse 3D Blender scene:
```sh
blender -b blizniak_dwulokalowy.blend \
 --python houses/blizniak_dwulokalowy/import_blendkit_models.py -- \
 --manifest /private/placements.json \
 --asset-dir /private/downloaded-blends \
 --output /private/blizniak_staged.blend --format film
```

Until legitimate BlenderKit `.blend` files are available, this integration can prepare and validate the pipeline but cannot truthfully claim to have used Blendkit 3D assets in renders.

## Security
Never commit authorization headers, cookies, user API keys, paid or Royalty Free model binaries, signed download URLs, or customer drawings to public repo.
