"""Inventory fresh room assets vs previous LUXORIA CC0 v1, not downloads."""
import json, urllib.request, urllib.parse, collections, pathlib
UA="Luxoria-Interior-Catalogue-v2/1.0"
BASE="https://github.com/RealAipl/openhouse-3d/releases/download/luxoria-interior-megapack-cc0-v1/LUXORIA_Manifest_Licencje_i_Zrodla.json"
def read(url):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=50) as r: return json.load(r)
old=read(BASE)
prev={x["id"] for x in old["assets"]}
print("Previous v1",len(prev), "models",old["models"],"textures",old["pbr_materials"])
for kind in ("models","textures"):
 data=read("https://api.polyhaven.com/assets?type="+kind)
 missing={k:v for k,v in data.items() if k not in prev}
 print(kind,"total",len(data),"not in v1",len(missing))
 categories=collections.Counter(str(i.get("category")) for i in missing.values())
 print(kind,"top categories NOT IN V1",categories.most_common(30))
 print(kind,"NAME EXAMPLES",[(slug,d.get("name","")) for slug,d in list(missing.items())[:20]])
try:
 ambient=read("https://ambientcg.com/api/v2/full_json?type=Material&limit=5&sort=Popular")
 print("ambientCG v2 keys",list(ambient)[:18],"count",ambient.get("numberOfResults"))
 vals=ambient.get("foundAssets",[])
 print("ambientCG first asset sample",json.dumps(vals[0],ensure_ascii=False)[:2600] if vals else "none")
except Exception as e:
 print("ambientCG v2 error",type(e).__name__,str(e)[:500])
try:
 ambient=read("https://ambientcg.com/api/v3/assets?type=Material&limit=3")
 print("ambientCG v3 keys",list(ambient)[:18],"sample",json.dumps(ambient,ensure_ascii=False)[:1500])
except Exception as e:
 print("ambientCG v3 error",type(e).__name__,str(e)[:500])
