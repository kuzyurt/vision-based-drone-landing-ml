"""Interrupted review exports are preserved, and stale videos are never reused."""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from . import review
from .config import review_scenarios

class ReviewChecks(unittest.TestCase):
    def test_interrupted_export_is_quarantined_without_self_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);destination=root/'review';scenario=review_scenarios()[0]
            partial=destination/scenario.name;partial.mkdir(parents=True)
            (partial/'steps.jsonl').write_text('preserve crashed recording')
            def flight(s,directory):
                directory=Path(directory);self.assertFalse(directory.exists());directory.mkdir()
                result={'scenario':asdict(s),'outcome':'landed','records':2,'runtime_source_sha256':'fixture-runtime'}
                (directory/'summary.json').write_text(json.dumps(result));(directory/'review.mp4').write_bytes(b'fixture')
                Image.new('RGB',(640,360)).save(directory/'frame_0000.jpg');return result
            with patch.object(review,'ROOT',root),patch.object(review,'source_fingerprint',return_value='fixture-runtime'),patch.object(review,'run_episode',flight),patch('landing_training.collection_benchmark.check_ports'):
                result=review.export_reviews(destination,limit=1)
            saved=list((destination/'partial_attempts').glob('*/steps.jsonl'))
            self.assertEqual(len(saved),1);self.assertEqual(saved[0].read_text(),'preserve crashed recording')
            self.assertFalse(result['qualification_passed']);self.assertFalse((destination/'approval.json').exists())
            self.assertFalse(any('partial_attempts' in key for key in result['artifacts']))

    def test_complete_stale_video_is_preserved_and_requires_new_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            destination=Path(folder);scenario=review_scenarios()[0];directory=destination/scenario.name;directory.mkdir()
            (directory/'summary.json').write_text(json.dumps({'failure':None,'runtime_source_sha256':'old'}))
            (directory/'review.mp4').write_bytes(b'stale-preserved')
            with patch.object(review,'source_fingerprint',return_value='new'),patch.object(review,'run_episode') as flight:
                with self.assertRaisesRegex(RuntimeError,'Runtime changed'):review.export_reviews(destination,limit=1)
            flight.assert_not_called();self.assertEqual((directory/'review.mp4').read_bytes(),b'stale-preserved')

    def test_occupied_ports_block_retry_before_moving_partial_recordings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);scenario=review_scenarios()[0];partial=root/scenario.name;partial.mkdir()
            (partial/'steps.jsonl').write_text('live-recording-preserved')
            with patch('landing_training.collection_benchmark.check_ports',side_effect=RuntimeError('occupied port')):
                with self.assertRaisesRegex(RuntimeError,'occupied port'):review.export_reviews(root,limit=1)
            self.assertEqual((partial/'steps.jsonl').read_text(),'live-recording-preserved')
            self.assertFalse((root/'partial_attempts').exists())

if __name__=='__main__':unittest.main()
