"""Render the saved 3D camera animation as native frames, with resumable outputs."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'houses/blizniak_dwulokalowy/output/refined'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames', default='1,240,480')
    parser.add_argument('--samples', type=int, default=16)
    parser.add_argument('--time-limit', type=float, default=0)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    args = parser.parse_args(__import__('sys').argv[__import__('sys').argv.index('--')+1:])
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Wnetrza_4_lokale.blend'))
    scene = bpy.context.scene
    scene.camera = bpy.data.objects['Spacer_3D_A2']
    for key in ['A_ground', 'A_upper', 'B_ground', 'B_upper']:
        bpy.data.collections['Lokal_' + key].hide_render = key != 'A_upper'
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 20
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 8
    scene.render.use_persistent_data = True
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.adaptive_threshold = .08
    scene.cycles.time_limit = args.time_limit
    scene.cycles.use_denoising = True
    scene.cycles.denoising_quality = 'FAST'
    name = 'Film_klatki' if args.frames == 'all' else 'Film_kontrola_CYCLES'
    target = OUT / name
    target.mkdir(exist_ok=True)
    if args.frames == 'all':
        settings = {'blend_sha256': hashlib.sha256((OUT/'Wnetrza_4_lokale.blend').read_bytes()).hexdigest(),
                    'width':args.width, 'height':args.height, 'samples':args.samples,
                    'time_limit':args.time_limit, 'fps':24, 'frame_end':scene.frame_end,
                    'denoising_quality':'FAST'}
        manifest = target/'settings.json'
        if manifest.exists():
            assert json.loads(manifest.read_text()) == settings, 'Use a new directory after scene/settings changes'
        elif any(target.glob('*.png')):
            raise RuntimeError('Existing frames lack a settings fingerprint; verify before resuming')
        else:
            manifest.write_text(json.dumps(settings, indent=2))
    frames = range(1, scene.frame_end+1) if args.frames == 'all' else map(int, args.frames.split(','))
    records = []
    for frame in frames:
        path = target / f'{frame:04d}.png'
        if path.exists() and args.frames == 'all':
            continue
        scene.frame_set(frame)
        scene.render.filepath = str(path)
        start = time.monotonic()
        bpy.ops.render.render(write_still=True)
        records.append({'frame':frame, 'seconds':time.monotonic()-start})
        print('WALK_FRAME', frame, records[-1]['seconds'], flush=True)
        (target/'rendering.json').write_text(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
