"""Integrity checks for portable marker-policy bundles."""
import json,tempfile,unittest
from pathlib import Path
from .gate import file_hash
from .marker_bundle import read_bundle

class BundleChecks(unittest.TestCase):
    def fixture(self,root):
        checkpoint=root/'pose.pt';checkpoint.write_bytes(b'test checkpoint bytes')
        configuration={'schema':'aerodock.landing.marker_policy.v1','checkpoint':'pose.pt',
                       'checkpoint_sha256':file_hash(checkpoint),'source_files_sha256':{}}
        path=root/'policy.json';path.write_text(json.dumps(configuration))
        return path,checkpoint,configuration
    def test_checked_checkpoint_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path,checkpoint,_=self.fixture(Path(directory))
            _,selected=read_bundle(path);self.assertEqual(selected,checkpoint.resolve())
    def test_changed_checkpoint_is_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path,checkpoint,_=self.fixture(Path(directory));checkpoint.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'checksum'):read_bundle(path)
    def test_paths_cannot_escape_the_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,checkpoint,configuration=self.fixture(root)
            configuration['checkpoint']='../outside.pt';path.write_text(json.dumps(configuration))
            with self.assertRaisesRegex(ValueError,'inside'):read_bundle(path)
    def test_changed_policy_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path,_,configuration=self.fixture(Path(directory))
            configuration['source_files_sha256']={'marker_policy.py':'0'*64};path.write_text(json.dumps(configuration))
            with self.assertRaisesRegex(ValueError,'source changed'):read_bundle(path)
