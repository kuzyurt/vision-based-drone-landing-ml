"""Check bounded packaging and scenario coverage without rendering simulations."""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from .gate import safe_review_outcome
from .review_cases import diverse_review_scenarios
from .review_package import package,digest


class DiverseReviewChecks(unittest.TestCase):
    def test_cases_cover_production_bounds_and_three_fault_types(self):
        cases=diverse_review_scenarios()
        self.assertEqual(len(cases),10)
        self.assertEqual({case.kind for case in cases},{'island','beach','city','gravel','rock'})
        self.assertEqual(sum(case.initial_camera_target for case in cases),5)
        self.assertEqual(sum(bool(case.camera_blind_seconds or case.beacon_dropout_duration_s or case.dock_unavailable_seconds) for case in cases),3)
        self.assertTrue(any(case.distance<5 for case in cases))
        self.assertTrue(any(5<=case.distance<20 for case in cases))
        self.assertTrue(any(case.distance>50 for case in cases))
        self.assertEqual(max(case.height for case in cases),8)
        self.assertGreater(max(case.boat_speed for case in cases),.85)
        self.assertGreater(max(case.wind_mean_m_s for case in cases),3.5)
        self.assertGreater(max(case.wave_height for case in cases),.13)
        for index in range(0,10,2):
            a,b=cases[index:index+2]
            self.assertEqual((a.world_seed,a.path_seed,a.boat_start_fraction),(b.world_seed,b.path_seed,b.boat_start_fraction))
            self.assertEqual((a.reverse,b.reverse),(False,True))
            a.validate();b.validate()
        for outcome in ('water_strike','collision_failure'):
            self.assertFalse(safe_review_outcome({'outcome':outcome,'scenario':asdict(cases[3])}))
        self.assertTrue(safe_review_outcome({'outcome':'abort','scenario':asdict(cases[3])}))
        self.assertFalse(safe_review_outcome({'outcome':'abort','scenario':asdict(cases[0])}))

    def fixture(self,root,video_size):
        bundle=root/'bundle';bundle.mkdir();episodes=[]
        for index in range(10):
            name=f'fixture_{index}';directory=bundle/name;directory.mkdir()
            (directory/'review.mp4').write_bytes(bytes([index])*video_size)
            (directory/'steps.jsonl').write_text('{"recorded_fixture":true}\n')
            (directory/'scenario.json').write_text('{}');(directory/'summary.json').write_text('{}')
            (directory/'observations.h5').write_bytes(b'excluded-raw-fixture')
            episodes.append({'name':name,'video':name+'/review.mp4','records':25})
        (bundle/'manifest.json').write_text(json.dumps({'qualification_passed':True,'source_sha256':'unit-fixture','episodes':episodes}))
        (bundle/'index.html').write_text('<a href="fixture_0/observations.h5">Raw RGB</a>')
        return bundle

    def probe(self,*args):return {'width':1280,'height':720,'r_frame_rate':'25/1','nb_frames':'25'},1.

    def test_compact_archive_keeps_telemetry_and_preserves_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bundle=self.fixture(root,100);archive=root/'preview.zip'
            before=digest(bundle/'fixture_0/review.mp4')
            with patch('landing_training.review_package.probe',side_effect=self.probe):result=package(bundle,archive,max_mb=2)
            self.assertFalse(result['reencoded']);self.assertLess(result['archive_MB'],2)
            self.assertEqual(digest(bundle/'fixture_0/review.mp4'),before)
            with ZipFile(archive) as packed:
                self.assertIsNone(packed.testzip())
                self.assertEqual(sum(name.endswith('steps.jsonl') for name in packed.namelist()),10)
                self.assertFalse(any(name.endswith('.h5') for name in packed.namelist()))
                self.assertNotIn('observations.h5',packed.read('index.html').decode())
            self.assertTrue(Path(result['checksum_file']).exists())

    def test_oversized_archive_reencodes_copies_with_parallel_encoder(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bundle=self.fixture(root,300000);archive=root/'preview.zip'
            originals={str(path):digest(path) for path in bundle.glob('*/review.mp4')}
            calls=[]
            def ffmpeg(command,**kwargs):
                calls.append(command)
                if command[command.index('-pass')+1]=='2':Path(command[-1]).write_bytes(b'encoded-fixture'*1000)
            with patch('landing_training.review_package.probe',side_effect=self.probe),patch('landing_training.review_package.subprocess.run',side_effect=ffmpeg):
                result=package(bundle,archive,max_mb=2,workers=4)
            self.assertTrue(result['reencoded']);self.assertLess(result['archive_MB'],2)
            self.assertEqual(len(calls),20)
            self.assertEqual(originals,{str(path):digest(path) for path in bundle.glob('*/review.mp4')})

    def test_missing_qualification_and_impossible_size_never_publish_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bundle=self.fixture(root,300000);archive=root/'preview.zip'
            with patch('landing_training.review_package.probe',side_effect=self.probe):
                with self.assertRaisesRegex(ValueError,'too small'):package(bundle,archive,max_mb=.01)
            self.assertFalse(archive.exists());self.assertFalse(list(root.glob('*.partial')))
            manifest=json.loads((bundle/'manifest.json').read_text());manifest['qualification_passed']=False
            (bundle/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'qualified'):package(bundle,archive)
            self.assertFalse(archive.exists())


if __name__=='__main__':unittest.main()
