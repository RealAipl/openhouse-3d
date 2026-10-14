"""Create a genuinely moving-camera 3D film from the separately rendered Cycles shots.

Render pipeline: Blender Cycles 960x540 at sampled ~4 fps -> optical flow
interpolation to 24 fps -> Lanczos upscale to 1280x720 -> captions and cut.
NO fake image-only tour or proprietary AI API.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

from .house import SHOTS, ROOM_META

ROOT = Path(__file__).resolve().parent
DRAFT = ROOT / "output" / "film" / "draft"
OUT = ROOT / "output" / "film" / "final"
OUT.mkdir(parents=True, exist_ok=True)
SEGMENTS = OUT / "segments"
SEGMENTS.mkdir(exist_ok=True)
CAPTIONS = OUT / "captions"
CAPTIONS.mkdir(exist_ok=True)
FFMPEG = get_ffmpeg_exe()
FONTPATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def run(command):
    print("$", " ".join(str(x) for x in command), flush=True)
    subprocess.run(command, check=True)


def main():
    # A missing room is fatal; do not ship a partial movie under "all apartments".
    assert len(SHOTS)==27
    rooms={s["name"][len("visit_"):] for s in SHOTS if s["name"].startswith("visit_")}
    assert rooms==set(ROOM_META), ("Coverage incomplete",rooms.symmetric_difference(ROOM_META))
    filters = subprocess.run([FFMPEG,"-hide_banner","-filters"],capture_output=True,text=True,check=True).stdout
    optical = "minterpolate" in filters
    overlay = "drawtext" in filters
    if not optical:
        print("WARN: optical flow unavailable, using frame duplication.", flush=True)
    assert shutil.which("fc-list") is not None, "fontconfig package required"
    assert Path(FONTPATH).exists(), "Caption font missing"

    clips=[]
    report={"scene":"blizniak_dwulokalowy","rooms":len(rooms),
            "shots":len(SHOTS),"interpolation":("minterpolate" if optical else "fps"),
            "resolution":"1280x720","fps":24,"source":"Blender Cycles, 960x540, approx 4 fps"}
    for shot in SHOTS:
        name=shot["name"]
        directory=DRAFT / name
        images=sorted(directory.glob("f_*.png"))
        assert len(images)>=4, f"{name}: not enough Blender 3D frames ({len(images)})"
        # Original shots are re-rendered with frame_step=6 at 24fps => 4 true 3D frames/s.
        frames=(6.0/24.0)*len(images)
        assert frames>=.75
        caption=CAPTIONS/(name+".txt")
        caption.write_text((shot.get("caption") or "").replace("_"," "),encoding="utf-8")
        dest=SEGMENTS/(name+".mp4")
        filt="scale=1280:720:flags=lanczos,"
        if optical:
            filt+="minterpolate=fps=24:mi_mode=mci:mc_mode=obmc:me_mode=bidir,"
        else:
            filt+="fps=24,"
        filt+="eq=contrast=1.04:saturation=1.04,"
        if overlay and shot.get("caption"):
            filt+="drawbox=x=0:y=638:w=1280:h=82:color=black@0.54:t=fill,"
            filt+=(f"drawtext=fontfile={FONTPATH}:textfile={caption}:"
                   "fontsize=24:fontcolor=white:shadowx=1:shadowy=1:"
                   "x=42:y=h-52,")
        filt+="format=yuv420p"
        run([FFMPEG,"-hide_banner","-loglevel","error","-y",
             "-framerate","4","-pattern_type","glob","-i",str(directory/"f_*.png"),
             "-vf",filt,"-r","24",
             "-c:v","libx264","-preset","fast","-crf","20",
             "-pix_fmt","yuv420p","-t",str(shot["sec"]),
             "-movflags","+faststart",str(dest)])
        assert dest.exists() and dest.stat().st_size>7000, "Bad film segment "+name
        clips.append(dest)

    # Return to the same exterior at the end for a proper final view.
    clips.append(SEGMENTS/"exterior_front.mp4")
    ffconcat=OUT/"segments.ffconcat"
    ffconcat.write_text("ffconcat version 1.0\n" +
                        "".join("file '"+str(c.resolve())+"'\n" for c in clips),encoding="utf-8")
    final=OUT/"blizniak_4_lokale_cycles_walkthrough_720p.mp4"
    run([FFMPEG,"-hide_banner","-loglevel","error","-y",
         "-safe","0","-f","concat","-i",str(ffconcat),
         "-c","copy","-movflags","+faststart",str(final)])
    assert final.stat().st_size>1_000_000,"Final film is unexpectedly small"
    from archviz import filmkit
    filmkit.configure(str(ROOT/"output"/"film"), "draft")
    filmkit.contact_sheet(str(OUT/"contact_sheet.jpg"),SHOTS,per_shot=2)
    report["output"]=str(final)
    report["size_bytes"]=final.stat().st_size
    report["segment_count"]=len(clips)
    (OUT/"film_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("FINISHED:",json.dumps(report,indent=2),flush=True)


if __name__=="__main__":
    main()
