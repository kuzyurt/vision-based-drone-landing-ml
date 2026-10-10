"""Approval reuse is limited to unchanged, previously inspected runtime/data."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from . import gate


class ApprovalReuseChecks(unittest.TestCase):
    def fixture(self, root):
        # Synthetic unit evidence only; never approve generated real recordings.
        episodes=[{'name':f'fixture_{index}'} for index in range(10)]
        qualification=root/'qualification.json'
        qualification.write_text(json.dumps({'passed':True,'runtime_source_sha256':'runtime'}))
        artifacts={'qualification.json':gate.file_hash(qualification)}
        for episode in episodes:
            path=root/episode['name']/'summary.json';path.parent.mkdir()
            path.write_text(json.dumps({'runtime_source_sha256':'runtime','outcome':'landed','failure':None}))
            artifacts[str(path.relative_to(root))]=gate.file_hash(path)
        manifest={'source_sha256':'old-reporting-code','qualification_passed':True,
                  'episodes':episodes,'artifacts':artifacts,'collection_plan':{'fixture_plan':True}}
        (root/'manifest.json').write_text(json.dumps(manifest))
        (root/'approval.json').write_text(json.dumps({'status':'approved','reviewer':'unit-fixture',
            'manifest_sha256':gate.file_hash(root/'manifest.json'),
            'reviewed_episodes':sorted(episode['name'] for episode in episodes)}))
        return manifest

    def test_reuse_preserves_original_approval_and_requires_explicit_option(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest=self.fixture(root)
            before={name:gate.file_hash(root/name) for name in ('manifest.json','approval.json')}
            with patch.object(gate,'source_fingerprint',side_effect=lambda runtime_only=False:'runtime' if runtime_only else 'new-code'),patch('landing_training.collect.planned_scenarios',return_value={'fixture_plan':True}):
                with patch.dict(os.environ,{'LANDING_REUSE_APPROVED_RUNTIME':'0'}):
                    with self.assertRaisesRegex(PermissionError,'Source/assets changed'):gate.require_approval(root)
                with patch.dict(os.environ,{'LANDING_REUSE_APPROVED_RUNTIME':'1'}):
                    self.assertEqual(gate.require_approval(root),manifest)
                    self.assertEqual(before,{name:gate.file_hash(root/name) for name in before})
                    (root/'fixture_0/summary.json').write_text('tampered')
                    with self.assertRaisesRegex(PermissionError,'artifact missing or changed'):gate.require_approval(root)

    def test_runtime_plan_changes_and_missing_approval_are_blocked(self):
        for changed in ('runtime','plan','missing_approval'):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);self.fixture(root)
                if changed=='missing_approval':(root/'approval.json').unlink()
                with patch.dict(os.environ,{'LANDING_REUSE_APPROVED_RUNTIME':'1'}),patch.object(gate,'source_fingerprint',side_effect=lambda runtime_only=False:('changed-runtime' if changed=='runtime' else 'runtime') if runtime_only else 'new-code'),patch('landing_training.collect.planned_scenarios',return_value={'changed':True} if changed=='plan' else {'fixture_plan':True}):
                    with self.assertRaises(PermissionError):gate.require_approval(root)


if __name__=='__main__':unittest.main()
