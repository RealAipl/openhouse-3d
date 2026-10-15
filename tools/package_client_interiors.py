"""Package approved interior renders into a client album, gallery, film and ZIP.

Uses the existing cloud runtime's Pillow/reportlab and FFmpeg. No remote service.
"""
import argparse
import hashlib
import html
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'houses/blizniak_dwulokalowy/output/final'
DELIVERY=OUT/'Wnetrza_bliźniaka'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
VIEWS=[
 ('01_pietro_salon','Salon na piętrze','Strefa wypoczynku · lokal A2'),
 ('02_pietro_kuchnia_jadalnia','Kuchnia i jadalnia na piętrze','Otwarta strefa dzienna · lokal A2'),
 ('04_parter_salon','Salon na parterze','Strefa dzienna · lokal A1'),
 ('05_parter_kuchnia','Kuchnia na parterze','Zabudowa w układzie L · lokal A1'),
 ('06_sypialnia_glowna','Sypialnia główna','Pokój z podwójnym łóżkiem · lokal A2'),
 ('08_pokoj_goscinny_gabinet','Drugi pokój','Pokój gościnny z miejscem do pracy · lokal A1'),
 ('09_lazienka','Łazienka','Strefa umywalki, WC i prysznica · lokal A2'),
 ('11_hol','Hol','Komunikacja między pomieszczeniami · lokal A2'),
 ('12_wiatrolap_pietro','Wiatrołap','Strefa wejścia · lokal A2'),
]


def filecopy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)


def prepare():
    DELIVERY.mkdir(exist_ok=True)
    for stem,title,sub in VIEWS:
        source=OUT/'Obrazy'/(stem+'.png')
        with Image.open(source) as im:
            assert im.size==(1920,1080),source
            im.verify()
        filecopy(source,DELIVERY/'Wizualizacje/PNG'/source.name)
        p=DELIVERY/'Wizualizacje/JPG'/(stem+'.jpg');p.parent.mkdir(parents=True,exist_ok=True)
        Image.open(source).convert('RGB').save(p,quality=96,subsampling=0)
    filecopy(OUT/'Wnetrza_4_lokale.blend',DELIVERY/'Model/Wnetrza_4_lokale.blend')
    filecopy(OUT/'README.md',DELIVERY/'README.md')
    for name in ['Kontrola_rzutow.png','KONTROLA_GEOMETRII.json','KONTROLA_PLIKU_BLEND.json','KONTROLA_WIDOCZNOSCI_PIONU.json','KONTROLA_WIDOCZNOSCI_DRZWI.json','ODCZYT_RYSUNKOW.json','ZRODLA_MODELI.json','ZRODLA_MATERIALOW.json']:
        filecopy(OUT/name,DELIVERY/'Dokumentacja'/name)
    filecopy(OUT/'Obrazy/render_times.json',DELIVERY/'Dokumentacja/RENDERING.json')
    filecopy(ROOT/'LICENSE',DELIVERY/'Zrodla/LICENSE_MIT.txt')
    for name in ['plan.py','architecture.py','interiors.py','client_interiors.py']:
        filecopy(ROOT/'houses/blizniak_dwulokalowy'/name,DELIVERY/'Zrodla/house'/name)
    for name in ['check_client_interiors.py','package_client_interiors.py']:
        filecopy(ROOT/'tools'/name,DELIVERY/'Zrodla/tools'/name)


def sheet():
    canvas=Image.new('RGB',(1800,1370),'#f7f6f2');d=ImageDraw.Draw(canvas)
    d.text((42,25),'WNĘTRZA BLIŹNIAKA',font=ImageFont.truetype(BOLD,35),fill='#202d29')
    d.text((42,77),'Cztery lokale · dwa segmenty · reprezentatywne aranżacje',font=ImageFont.truetype(FONT,22),fill='#58625a')
    for i,(stem,title,sub) in enumerate(VIEWS):
        x=42+(i%3)*578;y=140+(i//3)*390
        im=Image.open(OUT/'Obrazy'/(stem+'.png')).resize((558,314),Image.Resampling.LANCZOS)
        canvas.paste(im,(x,y))
        d.text((x,y+324),title,font=ImageFont.truetype(BOLD,21),fill='#202d29')
        d.text((x,y+355),sub.split(' · ')[-1],font=ImageFont.truetype(FONT,17),fill='#58625a')
    d.text((42,1320),'Propozycja aranżacji wnętrz na podstawie dostarczonego projektu koncepcyjnego.',font=ImageFont.truetype(FONT,18),fill='#58625a')
    canvas.save(DELIVERY/'Podglad_wnetrz.jpg',quality=94)


def album():
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import ImageReader
    pdfmetrics.registerFont(TTFont('Interior',FONT));pdfmetrics.registerFont(TTFont('InteriorBold',BOLD))
    W,H=841.89,595.28
    c=canvas.Canvas(str(DELIVERY/'Prezentacja_wnetrz.pdf'),pagesize=(W,H))
    c.setTitle('Wnętrza bliźniaka - propozycja aranżacji');c.setAuthor('RealAI')
    for i,(stem,title,sub) in enumerate(VIEWS):
        c.setFillColor(HexColor('#f7f6f2'));c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(HexColor('#25322d'));c.setFont('InteriorBold',22);c.drawString(32,H-39,title)
        c.setFont('Interior',10);c.setFillColor(HexColor('#627066'));c.drawString(32,H-60,sub)
        c.drawImage(ImageReader(str(OUT/'Obrazy'/(stem+'.png'))),32,85,width=W-64,height=(W-64)*9/16)
        c.setFont('Interior',8);c.drawString(32,53,'WNĘTRZA BLIŹNIAKA  /  PROPOZYCJA ARANŻACJI')
        c.drawRightString(W-32,53,f'{i+1:02d} / 11')
        c.setFont('Interior',7.6);c.drawString(32,31,'Segment B odzwierciedla układ segmentu A. Materiały i wyposażenie są propozycją, a nie standardem sprzedaży.')
        c.showPage()
    c.setFillColor(HexColor('#f7f6f2'));c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(HexColor('#25322d'));c.setFont('InteriorBold',22);c.drawString(32,H-39,'Układ porównany z dokumentacją')
    c.setFont('Interior',10);c.drawString(32,H-61,'Obrysy faktycznych ścian z pliku Blender na tle oryginalnych rzutów.')
    # Fit the visual evidence rather than distorting its proportions.
    im=Image.open(OUT/'Kontrola_rzutow.png');iw,ih=im.size
    dh=435;dw=dh*iw/ih;c.drawImage(ImageReader(im),(W-dw)/2,55,width=dw,height=dh)
    c.setFont('Interior',8);c.drawRightString(W-32,31,'10 / 11');c.showPage()
    c.setFillColor(HexColor('#f7f6f2'));c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(HexColor('#25322d'));c.setFont('InteriorBold',23);c.drawString(40,H-50,'Zakres i informacje do projektu')
    c.setFont('InteriorBold',13);c.drawString(40,H-89,'Cztery kompletne lokale w edytowalnym modelu')
    def lines(text,y,size=10.5,maxw=750):
        c.setFont('Interior',size);c.setFillColor(HexColor('#46554c'))
        words=text.split();line=''
        for word in words:
            test=(line+' '+word).strip()
            if pdfmetrics.stringWidth(test,'Interior',size)>maxw:
                c.drawString(40,y,line);y-=17;line=word
            else:line=test
        if line:c.drawString(40,y,line);y-=17
        return y
    y=lines('Dwa lustrzane segmenty, parter i piętro, 24 pomieszczenia. Parter: dwa pokoje i salon z aneksem. Piętro: jeden pokój i większy salon z aneksem. Zestaw pokazuje reprezentatywne ujęcia segmentu A.',H-111)
    y-=20;c.setFont('InteriorBold',13);c.setFillColor(HexColor('#25322d'));c.drawString(40,y,'Co skorygowano po porównaniu z rysunkami');y-=23
    y=lines('Głębokość 9,44 m, podział stref 4,54 / 0,18 / 3,94 m, tylna sypialnia 3,44 x 3,94 m, hol 1,57 m, wiatrołapy i pomieszczenie gospodarcze, uskok instalacyjny łazienek, stolarka oraz zabudowa kuchenna L.',y)
    y-=20;c.setFont('InteriorBold',13);c.setFillColor(HexColor('#25322d'));c.drawString(40,y,'Rozbieżność w źródle i granice dokładności');y-=23
    y=lines('Na piętrze etykieta salonu 4,14 m jest sprzeczna z łańcuchem zewnętrznym 4,54 m oraz tabelą 33,32 m². Przyjęto 4,54 m. Wymaga to potwierdzenia autora projektu przed użyciem do prac wykonawczych.',y)
    y=lines('Brak przekroju: wysokość sufitu 2,69 m jest założeniem. Rysunki są rastrowe; niektóre pozycje otworów odczytano graficznie. Model nie zastępuje CAD ani dokumentacji wykonawczej. Widok za oknami jest neutralnym tłem.',y-8)
    y-=20;c.setFont('InteriorBold',13);c.setFillColor(HexColor('#25322d'));c.drawString(40,y,'W paczce');y-=23
    lines('9 wizualizacji PNG i JPG w 1920 x 1080, plik Blender z teksturami, film prezentacyjny z wizualizacji, lokalna galeria, odczyt rysunków, kontrola modelu, źródła i licencje zasobów CC0. Film jest montażem obrazów, a nie interaktywnym spacerem.',y)
    c.setFont('Interior',8);c.drawString(40,31,'Wyłącznie wnętrza. Bez zmian witryny LUXORIA i bez nowych wizualizacji zewnętrznych.');c.drawRightString(W-32,31,'11 / 11')
    c.save()


def gallery():
    cards='\n'.join(f'<button class="card" data-index="{i}"><img src="Wizualizacje/JPG/{stem}.jpg" alt="{html.escape(title)}"><span><b>{title}</b><small>{sub}</small></span></button>' for i,(stem,title,sub) in enumerate(VIEWS))
    names=json.dumps([{'src':f'Wizualizacje/PNG/{stem}.png','title':title} for stem,title,sub in VIEWS],ensure_ascii=False)
    page='''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Wnętrza bliźniaka</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f5f0;color:#24302a;font:17px/1.6 system-ui,sans-serif}main{max-width:1420px;margin:auto;padding:60px 5vw}h1{font-size:clamp(34px,5vw,66px);letter-spacing:-.055em;line-height:1.05;margin:20px 0}p{max-width:760px;color:#657069}a{color:inherit}nav{display:flex;gap:22px;flex-wrap:wrap;margin:30px 0 45px}nav a{padding:9px 0;border-bottom:1px solid #aab2aa;text-decoration:none}.grid{display:grid;grid-template-columns:1fr 1fr;gap:30px}.card{border:0;text-align:left;background:white;padding:0;cursor:zoom-in;color:inherit;font:inherit}.card img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover}.card span{display:block;padding:18px 22px}.card small{display:block;font-size:14px;color:#657069;margin-top:4px}footer{margin-top:60px;border-top:1px solid #d7dbd3;padding-top:24px;max-width:1000px;color:#657069;font-size:14px}dialog{border:0;padding:12px;background:#101512;color:white;width:96vw;max-width:1500px}dialog::backdrop{background:#000c}dialog img{width:100%;max-height:80vh;object-fit:contain}dialog div{display:flex;align-items:center;justify-content:space-between;gap:12px}dialog button{background:transparent;border:1px solid #88968b;color:white;padding:8px 16px;cursor:pointer;font:inherit}button:focus-visible,a:focus-visible{outline:3px solid #7a9883;outline-offset:4px}@media(max-width:720px){main{padding-top:24px}.grid{grid-template-columns:1fr;gap:20px}nav{gap:16px}}</style><main><small>PROPOZYCJA ARANŻACJI WNĘTRZ</small><h1>Jasne wnętrza.<br>Spójny charakter.</h1><p>Cztery niezależne lokale w dwóch segmentach. Poniżej reprezentatywne wnętrza parteru i piętra, opracowane na podstawie dostarczonych rzutów.</p><nav><a href="Prezentacja_wnetrz.pdf">Prezentacja PDF</a><a href="Film/Wnetrza_prezentacja_1080p.mp4">Film wnętrz</a><a href="Model/Wnetrza_4_lokale.blend">Model Blender</a><a href="README.md">Opis i zakres</a></nav><section class="grid">CARDS</section><footer>Segment B stanowi lustrzane odbicie segmentu A. Wszystkie cztery lokale są umeblowane w modelu. Materiały i wyposażenie to propozycja aranżacji, a nie standard sprzedaży. Rysunek piętra zawiera rozbieżność 4,14 / 4,54 m; przyjęto wartość zgodną z łańcuchem wymiarowym i zestawieniem powierzchni. Wysokość sufitu jest założeniem. Szczegóły i kontrola w README.</footer></main><dialog id="viewer"><img id="full" alt=""><div><button id="prev" aria-label="Poprzedni obraz">←</button><span id="caption"></span><button id="next" aria-label="Następny obraz">→</button><button id="close">Zamknij</button></div></dialog><script>const items=ITEMS;let at=0;const dialog=document.querySelector('#viewer');function show(i){at=(i+items.length)%items.length;document.querySelector('#full').src=items[at].src;document.querySelector('#full').alt=items[at].title;document.querySelector('#caption').textContent=items[at].title}document.querySelectorAll('.card').forEach(b=>b.onclick=()=>{show(+b.dataset.index);dialog.showModal()});document.querySelector('#prev').onclick=()=>show(at-1);document.querySelector('#next').onclick=()=>show(at+1);document.querySelector('#close').onclick=()=>dialog.close();document.addEventListener('keydown',e=>{if(dialog.open&&e.key==='ArrowRight')show(at+1);if(dialog.open&&e.key==='ArrowLeft')show(at-1)});</script></html>'''
    (DELIVERY/'Galeria.html').write_text(page.replace('CARDS',cards).replace('ITEMS',names))


def film():
    temp=OUT/'film-encode';temp.mkdir(exist_ok=True)
    clips=[]
    for i,index in enumerate([0,1,2,4,5,6]):
        stem,title,sub=VIEWS[index]
        plate=Image.new('RGBA',(1920,1080));d=ImageDraw.Draw(plate)
        for y in range(770,1080):d.line((0,y,1919,y),fill=(16,24,19,int(150*(y-770)/310)))
        d.text((82,914),title,font=ImageFont.truetype(BOLD,43),fill='white')
        d.text((85,978),sub,font=ImageFont.truetype(FONT,23),fill='#f0f2ed')
        overlay=temp/f'title-{i}.png';plate.save(overlay)
        clip=temp/f'clip-{i}.mp4'
        vf="[0:v]scale=2560:1440,zoompan=z='min(zoom+0.00030,1.036)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=120:s=1920x1080:fps=24[bg];[bg][1:v]overlay=0:0,fade=t=in:st=0:d=0.35,fade=t=out:st=4.65:d=0.35,format=yuv420p[v]"
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(OUT/'Obrazy'/(stem+'.png')),'-i',str(overlay),'-filter_complex',vf,'-map','[v]','-frames:v','120','-an','-c:v','libx264','-preset','fast','-crf','19','-threads','4',str(clip)],check=True)
        clips.append(clip)
    concat=temp/'list.txt';concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in clips))
    target=DELIVERY/'Film/Wnetrza_prezentacja_1080p.mp4';target.parent.mkdir(exist_ok=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(target)],check=True)


def archive():
    lines=[]
    for p in sorted(DELIVERY.rglob('*')):
        if p.is_file() and p.name!='SHA256SUMS.txt':lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(DELIVERY)))
    (DELIVERY/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
    zip_path=OUT/'Wnetrza_blizniaka_KOMPLET.zip'
    with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for p in sorted(DELIVERY.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(DELIVERY.parent)))
    with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
    print('PACKAGE_OK',zip_path,zip_path.stat().st_size)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--film',action='store_true');args=ap.parse_args()
    prepare();sheet();album();gallery()
    if args.film:film()
    archive()
