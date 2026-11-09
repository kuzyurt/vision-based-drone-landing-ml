"""Export the verified historical Tidewater flight without running simulation.

Requires ffmpeg/ffprobe on PATH. CPU encoding is restricted to one thread.
Original footage and experiment receipts are read-only inputs.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'tidewater-game/history/tidewater_20261011/policy_tidewater_windy_reef.mp4'
REPORT = ROOT/'tidewater-game/history/tidewater_20261011/pilot_results.json'
OUT = ROOT/'docs/media'


def run(*args):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                    '-threads','1','-filter_threads','1','-filter_complex_threads','1',
                    *map(str,args)], check=True)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-only',action='store_true',help='Reuse the completed MP4; regenerate lightweight preview, poster and receipt.')
    args=parser.parse_args()
    report=json.loads(REPORT.read_text(encoding='utf-8'))
    flight=next(x for x in report['metrics'] if x['name']=='tidewater_windy_reef')
    assert flight['outcome']=='landed' and sha(SOURCE)==flight['video_sha256']
    OUT.mkdir(parents=True,exist_ok=True)
    video=OUT/'tidewater-landing-1080p.mp4'
    if args.preview_only:
        previous=json.loads((OUT/'tidewater-landing-provenance.json').read_text(encoding='utf-8'))
        assert previous['source_sha256']==flight['video_sha256']
        assert sha(video)==previous['outputs'][video.name]['sha256'], 'Existing MP4 differs from its export receipt'
    if not args.preview_only:
        run('-i',SOURCE,'-vf','scale=1920:1080:flags=lanczos','-an','-c:v','libx264',
            '-preset','fast','-crf','22','-threads','1','-pix_fmt','yuv420p',
            '-movflags','+faststart',video)
        print('1080p video encoded.',flush=True)
    preview=OUT/'tidewater-landing-preview.gif'
    run('-ss','16','-i',SOURCE,'-filter_complex',
        '[0:v]setpts=0.5*PTS,fps=8,scale=640:360:flags=lanczos,split[a][b];'
        '[a]palettegen=max_colors=64:stats_mode=diff[p];'
        '[b][p]paletteuse=dither=none:diff_mode=rectangle',
        '-loop','0','-threads','1',preview)
    run('-ss','30','-i',SOURCE,'-frames:v','1','-vf','scale=1920:1080:flags=lanczos',
        '-threads','1',OUT/'tidewater-landing-poster.jpg')
    metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'stream=width,height,r_frame_rate:format=duration','-of','json',str(video)]))
    assert metadata['streams'][0]['width']==1920 and metadata['streams'][0]['height']==1080
    receipt=dict(source=str(SOURCE.relative_to(ROOT)).replace('\\','/'),
        source_sha256=sha(SOURCE),source_report=str(REPORT.relative_to(ROOT)).replace('\\','/'),
        source_flight=flight,policy_bundle_sha256=report['policy_bundle_sha256'],
        pose_checkpoint_sha256=report['pose_checkpoint_sha256'],recorded='2026-10-11',
        outcome='landed',model='historical frozen policy_bundle_v5; not R15 or the active search head',
        capture='Original spectator render 640x360, archived as 1280x720; upscale to 1920x1080.',
        presentation='Full third-person flight; no new flight, interpolation, or generated frames.',
        preview='Final approach and landing, source 16.0s to end, at 2x playback; 640x360, 8 fps, 64 colors. MP4 retains the full flight at 25 fps and real-time playback.',
        video=metadata,outputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p))
                               for p in [video,preview,OUT/'tidewater-landing-poster.jpg']})
    (OUT/'tidewater-landing-provenance.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print('Preview, poster and provenance written.',flush=True)
