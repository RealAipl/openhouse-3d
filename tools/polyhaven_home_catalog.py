#!/usr/bin/env python3
"""One-shot free CC0 photorealistic household asset inventory from Poly Haven API.

This is a discovery run, not an asset download. Metadata only.
Poly Haven public API credit: https://polyhaven.com (all actual models CC0).
"""
import json
import urllib.request
from pathlib import Path

URL="https://api.polyhaven.com/assets?type=models"
def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"OpenHouse3D-CC0-Interior-Research/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as resp:
        listing=json.load(resp)
    assert isinstance(listing,dict) and len(listing)>150, f"Unexpected API result: {len(listing)}"
    terms=("sofa","couch","arm chair","armchair","lounge chair","table","cabinet",
           "shelf","stool","lamp","light","bed","plant","vase","kettle","fridge",
           "sink","toilet","washing","microwave","cushion","basket","drawer",
           "television","desk","cup","bowl","books","pillow","coffee","mirror",
           "oven","bar chair","dining chair","towel","pot","chair","nightstand")
    result=[]
    for slug,meta in listing.items():
        name=str(meta.get("name",""))
        tags=" ".join(str(x) for x in (meta.get("tags") or []))
        cat=str(meta.get("category",""))
        hay=(name+" "+tags+" "+cat).lower()
        if not any(term in hay for term in terms):continue
        result.append({"id":slug,"name":name,"category":cat,"tags":meta.get("tags",[])[:7],
                       "downloads":meta.get("download_count",0),"attributes":meta.get("attributes",{})})
    result.sort(key=lambda a:(a["category"],a["name"]))
    outfile=Path("tmp/polyhaven_home_candidates.json")
    outfile.parent.mkdir(parents=True,exist_ok=True)
    outfile.write_text(json.dumps({"all_assets":len(listing),"matched":len(result),"candidates":result},
                                  ensure_ascii=False,indent=2),encoding="utf-8")
    print("Total models",len(listing),"candidate household models",len(result))
    for x in result:
        print(f'{x["id"]:42} {x["name"]:43} {x["category"]}')
    assert len(result)>=25,"Too few household models"
if __name__=="__main__":main()
