"""Downsample embedded viewer textures; keep the editable Blender file untouched."""
import argparse
import io
import json
import struct
from pathlib import Path
from PIL import Image


def optimize(source,target):
    data=source.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);bin_start=28+n;binary=data[bin_start:]
    image_views={im['bufferView']:im for im in doc.get('images',[]) if 'bufferView' in im};out=bytearray()
    for i,view in enumerate(doc['bufferViews']):
        start=view.get('byteOffset',0);payload=binary[start:start+view['byteLength']]
        if i in image_views:
            im=Image.open(io.BytesIO(payload));im.thumbnail((1024,1024),Image.Resampling.LANCZOS);stream=io.BytesIO()
            if 'A' in im.getbands() and im.getchannel('A').getextrema()!=(255,255):im.save(stream,format='PNG');mime='image/png'
            else:im.convert('RGB').save(stream,format='JPEG',quality=92,optimize=True);mime='image/jpeg'
            payload=stream.getvalue();image_views[i]['mimeType']=mime
        while len(out)%4:out.append(0)
        view['byteOffset']=len(out);view['byteLength']=len(payload);out.extend(payload)
    while len(out)%4:out.append(0)
    doc['buffers'][0]['byteLength']=len(out)
    for m in doc['materials']:
        if 'warm grey quartz' in m['name']:m.setdefault('pbrMetallicRoughness',{})['baseColorFactor']=[.40,.39,.36,1]
        if 'Light limestone bathroom' in m['name']:m.setdefault('pbrMetallicRoughness',{})['baseColorFactor']=[.42,.40,.36,1]
    j=json.dumps(doc,separators=(',',':')).encode()
    while len(j)%4:j+=b' '
    target.write_bytes(struct.pack('<III',0x46546c67,2,28+len(j)+len(out))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(out),0x004e4942)+out)
    print('VIEWER_TEXTURES',len(data),'->',target.stat().st_size)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('target',type=Path);a=p.parse_args();optimize(a.source,a.target)
