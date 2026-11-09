"""Create a bounded viewing ZIP while preserving the original review bundle."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED


def probe(path):
    result = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,r_frame_rate,nb_frames:format=duration',
        '-of', 'json', str(path)], text=True)
    value = json.loads(result)
    return value['streams'][0], float(value['format']['duration'])


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): value.update(block)
    return value.hexdigest()


def package(bundle, output, max_mb=80., workers=4):
    bundle = Path(bundle).resolve(); output = Path(output).resolve()
    if not math.isfinite(max_mb) or max_mb <= 0 or not 1 <= workers <= 8:
        raise ValueError('Positive finite size cap and 1..8 encoding workers required')
    if output.exists(): raise FileExistsError('Archive already exists: ' + str(output))
    if output.is_relative_to(bundle): raise ValueError('Keep the viewing archive outside the fingerprinted bundle')
    manifest = json.loads((bundle / 'manifest.json').read_text())
    if not manifest.get('qualification_passed') or len(manifest['episodes']) != 10:
        raise ValueError('Exactly ten qualified, audited review episodes required before packaging/upload')
    videos = [bundle / episode['video'] for episode in manifest['episodes']]
    if any(not path.resolve().is_relative_to(bundle) for path in videos): raise ValueError('Video escaped bundle')
    originals = {str(path): probe(path) for path in videos}
    for episode, path in zip(manifest['episodes'], videos):
        stream, _ = originals[str(path)]
        if (stream['width'], stream['height'], stream['r_frame_rate'], int(stream['nb_frames'])) != (1280, 720, '25/1', episode['records']):
            raise ValueError('Video/recording shape, clock or count mismatch')
    names = {'manifest.json', 'qualification.json', 'recording_audit.json', 'planned_collection.json',
             'approval.template.json', 'contact_sheet.jpg', 'index.html'}
    for episode in manifest['episodes']:
        name = episode['name']
        names.update(f'{name}/{file}' for file in ('review.mp4', 'steps.jsonl', 'scenario.json', 'summary.json'))
        names.update(str(path.relative_to(bundle)) for path in (bundle / name).glob('frame_*.jpg'))
    files = [bundle / name for name in sorted(names) if (bundle / name).is_file()]
    required = {f'{episode["name"]}/steps.jsonl' for episode in manifest['episodes']}
    if not required.issubset({str(path.relative_to(bundle)) for path in files}): raise ValueError('Missing input/output telemetry')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix('.zip.partial'); maximum = int(max_mb * 10**6)
    note = ('Viewing copy: ten videos with recorded input/output overlays, full JSONL telemetry and reports.\n'
            'Raw RGB HDF5 and PX4 logs remain in the original rendering-machine bundle.\n'
            'The original manifest describes that complete bundle; approval applies there.\n'
            'Video compression may differ in this ZIP. preview_manifest.json records viewing-video hashes.\n')

    def write_archive(mapping):
        preview = {'schema': 'aerodock.landing.review_preview.v1', 'original_bundle': str(bundle),
                   'original_manifest_sha256': digest(bundle / 'manifest.json'), 'raw_rgb_included': False,
                   'source_sha256': manifest['source_sha256'], 'videos': []}
        with ZipFile(partial, 'w', compression=ZIP_DEFLATED, compresslevel=6) as archive:
            for original in files:
                relative = str(original.relative_to(bundle)); current = mapping.get(str(original), original)
                if original.suffix == '.mp4':
                    preview['videos'].append({'path': relative, 'original_sha256': digest(original),
                                              'preview_sha256': digest(current),
                                              'reencoded': str(current) != str(original)})
                if relative == 'index.html':
                    html = re.sub(r'<a href="[^"]*/observations\.h5">[^<]*</a>',
                                  'Raw RGB remains on the rendering machine', original.read_text())
                    archive.writestr(relative, html)
                else:
                    archive.write(current, relative, compress_type=ZIP_STORED if original.suffix in ('.mp4', '.jpg', '.png') else ZIP_DEFLATED)
            archive.writestr('DOWNLOAD_NOTE.txt', note)
            archive.writestr('preview_manifest.json', json.dumps(preview, indent=2))
        return preview

    try:
        preview = write_archive({})
        if partial.stat().st_size > maximum:
            with ZipFile(partial) as archive:
                metadata = sum(item.compress_size for item in archive.infolist() if not item.filename.endswith('.mp4'))
            duration = sum(value[1] for value in originals.values())
            # Two-pass average bitrate preserves all frames and leaves 10% headroom.
            bitrate = int((maximum - metadata - 1024**2) * .9 * 8 / duration)
            if bitrate < 100_000: raise ValueError('Size limit is too small to retain readable 720p videos')
            with tempfile.TemporaryDirectory(prefix='review-encode-', dir=output.parent) as temporary:
                work = Path(temporary)
                def encode(item):
                    index, source = item; target = work / f'{index:02d}.mp4'; log = work / f'pass_{index:02d}'
                    common = ['ffmpeg', '-y', '-nostdin', '-loglevel', 'error', '-threads', '2', '-i', str(source),
                              '-an', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast',
                              '-b:v', str(bitrate), '-pix_fmt', 'yuv420p', '-passlogfile', str(log)]
                    subprocess.run(common + ['-pass', '1', '-f', 'null', os.devnull], check=True)
                    subprocess.run(common + ['-pass', '2', '-movflags', '+faststart', str(target)], check=True)
                    stream, _ = probe(target)
                    if stream != originals[str(source)][0]: raise ValueError('Compression changed frames, dimensions or clock')
                    return str(source), target
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    mapping = dict(executor.map(encode, enumerate(videos)))
                preview = write_archive(mapping)
        if partial.stat().st_size > maximum: raise ValueError('Compressed ZIP exceeds requested cap; no upload performed')
        with ZipFile(partial) as archive:
            if archive.testzip() is not None: raise ValueError('Archive checksum failed')
            if sum(name.endswith('/review.mp4') for name in archive.namelist()) != 10: raise ValueError('Archive does not contain ten videos')
            if any(name.endswith('.h5') for name in archive.namelist()): raise ValueError('Raw RGB unexpectedly included')
        partial.replace(output)
        checksum = output.with_suffix('.zip.sha256')
        checksum.write_text(digest(output) + '  ' + output.name + '\n')
        report = {'archive': str(output), 'archive_MB': output.stat().st_size / 10**6,
                  'max_MB': max_mb, 'videos': 10, 'reencoded': any(item['reencoded'] for item in preview['videos']),
                  'checksum_file': str(checksum), 'original_bundle': str(bundle)}
        output.with_suffix('.package.json').write_text(json.dumps(report, indent=2))
        return report
    finally:
        partial.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--max-mb', type=float, default=80.); parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(package(args.bundle, args.output, args.max_mb, args.workers), indent=2), flush=True)
