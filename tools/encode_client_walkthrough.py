"""Validate distinct native 3D frames, encode H.264, and decode the entire result."""
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'houses/blizniak_dwulokalowy/output/refined'


def main():
    folder = OUT/'Film_klatki'
    frames = [folder/f'{i:04d}.png' for i in range(1, 481)]
    hashes = set()
    for path in frames:
        with Image.open(path) as image:
            assert image.size == (1280, 720), (path, image.size)
            image.verify()
        hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    assert len(hashes) == 480, 'Repeated frames are not a native camera animation'
    target = OUT/'Wnetrza_spacer_3D_HD.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-xerror','-y',
                    '-framerate','24','-start_number','1','-i',str(folder/'%04d.png'),
                    '-frames:v','480','-vf','hqdn3d=1.2:1.2:3:3','-c:v','libx264',
                    '-preset','medium','-crf','17','-pix_fmt','yuv420p',
                    '-movflags','+faststart',str(target)], check=True)
    raw = subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0',
                                   '-show_entries','stream=width,height,r_frame_rate,nb_read_frames,duration',
                                   '-of','json',str(target)], text=True)
    stream = json.loads(raw)['streams'][0]
    assert stream['width'] == 1280 and stream['height'] == 720
    assert stream['r_frame_rate'] == '24/1' and int(stream['nb_read_frames']) == 480
    assert abs(float(stream['duration'])-20) < .01
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-xerror',
                    '-i',str(target),'-f','null','-'], check=True)
    report = {'native_distinct_3d_frames':len(hashes),'interpolated_frames':False,
              'source_resolution':[1280,720],'stream':stream,'full_decode_passed':True,
              'postprocessing':'Mild spatial/temporal denoising; no frame interpolation or upscaling',
              'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    (OUT/'KONTROLA_FILMU.json').write_text(json.dumps(report, indent=2))
    print('NATIVE_WALKTHROUGH_OK', report, flush=True)


if __name__ == '__main__':
    main()
