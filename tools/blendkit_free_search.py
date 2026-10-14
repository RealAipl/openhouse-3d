"""Small official Blendkit catalogue discovery for genuinely free CC0 models.

NO paid assets, NO bulk scraping, NO private API tokens, NO model redistribution.
Uses the same public search endpoint and query fields as vendor/Blendkit/search.py.
Outputs just author/title/license and file download URL metadata, never binaries.
"""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
from urllib import request, parse, error

BASE = "https://www.blendkit.com/api/v1/search/"
TERM_QUERIES = ("modern sofa", "dining table", "modern kitchen")
USER_AGENT = "OpenHouse3D-Blendkit-integration/1.0 (single limited CC0 research)"
MAX_ITEMS = 8

def search(phrase: str) -> dict:
    # Mirrors Blendkit query_to_url() model / is_free / license filters.
    query = parse.quote_plus(phrase) + "+asset_type:model+is_free:true+license:cc_zero"
    url = BASE + "?query=" + query + "&page_size=" + str(MAX_ITEMS) + "&dict_parameters=1"
    req = request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with request.urlopen(req, timeout=30) as res:
        if res.status != 200:
            raise RuntimeError(f"HTTP {res.status} during search")
        return json.load(res)

def record(asset: dict) -> dict | None:
    if str(asset.get("assetType", "")).lower()!="model":
        return None
    if asset.get("isFree") is not True:
        return None
    if asset.get("license","").lower() not in ("cc_zero", "cc0"):
        return None
    if asset.get("canDownload") is False:
        return None
    files = [f for f in asset.get("files",[]) if f.get("fileType") in
             ("blend","resolution_1K","resolution_2K","resolution_0_5K")
             and str(f.get("downloadUrl","")).startswith("https://")]
    if not files:
        return None
    chosen = sorted(files, key=lambda f:
                    ("resolution_1K","resolution_0_5K","resolution_2K","blend")
                    .index(f["fileType"]))[0]
    return {
        "id": asset.get("id"),"assetBaseId":asset.get("assetBaseId"),
        "name":asset.get("displayName") or asset.get("name"),
        "license":"cc_zero","isFree":True,
        "creator":asset.get("author",{}).get("firstName",""),
        "description":str(asset.get("description",""))[:260],
        "fileType":chosen["fileType"],
        "downloadUrl":chosen["downloadUrl"],
        "thumbnail": asset.get("thumbnailMiddleUrl"),
        "dimensions":{k:v for k,v in (asset.get("dictParameters") or {}).items()
                    if k in ("dimensionX","dimensionY","dimensionZ")},
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="tmp/blendkit_free_candidates.json")
    ap.add_argument("--strict",action="store_true")
    args=ap.parse_args()
    output={"source":BASE,"terms":{},"errors":{},"method":"free and CC0; <=8 results/term"}
    for phrase in TERM_QUERIES:
        try:
            raw=search(phrase)
            goods=[r for item in raw.get("results",[]) if (r:=record(item))]
            output["terms"][phrase]=goods
            print(f"FREE CC0 '{phrase}': {len(goods)} candidates out of <= {MAX_ITEMS}")
            for c in goods[:4]:
                print(" -",c["name"],c["assetBaseId"],c["fileType"])
        except (error.HTTPError,error.URLError,TimeoutError,ValueError,KeyError) as exc:
            output["errors"][phrase]=str(exc)[:250]
            print(f"Search unavailable for {phrase}: {exc}")
        time.sleep(1)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding="utf-8")
    if args.strict and not any(output["terms"].values()):
        raise SystemExit("No verified free CC0 downloadable models; cannot claim integration with actual model assets.")
    print("Saved",path)
if __name__=="__main__":main()
