"""Recording integrity and rendering equivalence for the optimized collector."""
from . import paths
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import h5py
import numpy as np
from .recording import Recorder
from .collection_benchmark import summarize

class CollectionChecks(unittest.TestCase):
    def test_buffer_owns_frames_and_flushes_partial_terminal_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder=Recorder(folder,{},batch_size=4)
            image=np.empty((360,640,3),np.uint8)
            for index in range(7):
                image.fill(index);row={'frame_index':index,'terminal':index==6}
                recorder.append(image,row)
                image.fill(255);row['frame_index']=-1
            recorder.close()
            rows=[json.loads(line) for line in (Path(folder)/'steps.jsonl').read_text().splitlines()]
            with h5py.File(Path(folder)/'observations.h5') as data:
                self.assertEqual(data['rgb'].shape,(7,360,640,3))
                for index,row in enumerate(rows):
                    self.assertEqual(row['frame_index'],index)
                    self.assertEqual(json.loads(data['steps'][index]),row)
                    self.assertTrue(np.all(data['rgb'][index]==index))
                self.assertTrue(rows[-1]['terminal'])
    def test_probe_has_no_production_projection(self):
        job={'max_rss_MiB':100,'hdf5_bytes':1000,'recorded_flight_s':4,
             'performance':{'stages_s':{'capture_s':2},'physics_s':1,'px4_sync_s':.5,'sensor_send_s':.1}}
        batches=[{'frames':101,'recording_span_s':5,'wall_s':15,'jobs':[job]}]
        self.assertIsNone(summarize(1,batches,1200,60,'quick')['projected_collection_hours'])
        self.assertEqual(summarize(1,batches,1200,60,'full')['projected_collection_hours'],5.)
    def test_bulk_mavlink_parse_preserves_fragmented_messages(self):
        from pymavlink.dialects.v20 import common as mavlink
        writer=mavlink.MAVLink(None,srcSystem=1,srcComponent=200)
        messages=[mavlink.MAVLink_hil_actuator_controls_message(1000*i,[.1*i]*16,128,0) for i in range(1,4)]
        packet=b''.join(message.pack(writer) for message in messages)
        byte_parser=mavlink.MAVLink(None);buffer_parser=mavlink.MAVLink(None)
        expected=[];actual=[]
        for byte in packet:
            message=byte_parser.parse_char(bytes([byte]))
            if message:expected.append(message.to_dict())
        for offset in range(0,len(packet),17):
            actual.extend(message.to_dict() for message in buffer_parser.parse_buffer(packet[offset:offset+17]) or ())
        self.assertEqual(actual,expected)
    def test_collection_gate_precedes_worker_and_directory_creation(self):
        from .collect import collect
        with tempfile.TemporaryDirectory() as folder:
            destination=Path(folder)/'must_not_exist'
            with self.assertRaises(PermissionError):collect(folder,destination,2,workers=2)
            self.assertFalse(destination.exists())
    def test_resume_recovers_complete_episode_but_rejects_missing_terminal(self):
        from dataclasses import asdict
        from .config import Scenario
        from .collect import _collect_locked
        scenario=asdict(Scenario(name='fixture_resume'))
        item={'scenario':scenario,'role':'training'}
        with tempfile.TemporaryDirectory() as folder:
            destination=Path(folder);bundle=destination/'review';bundle.mkdir()
            (bundle/'manifest.json').write_text('{}')
            episode=destination/scenario['name'];episode.mkdir()
            summary={'failure':None,'source_sha256':'fixture','scenario':scenario,'role':'training','training_eligible':True,'records':2,'outcome':'abort'}
            (episode/'summary.json').write_text(json.dumps(summary))
            recorder=Recorder(episode,scenario,'training')
            first={'frame_index':0,'observation':{'px4':{'armed':True}},'privileged':{'vertical_clearance_m':2}}
            terminal={'frame_index':1,'terminal':False,'outcome':'abort','output':{'executed_action':[0]*6,'action_supervision_valid':False}}
            image=np.zeros((360,640,3),np.uint8)
            recorder.append(image,first);recorder.append(image,terminal);recorder.close()
            with patch('landing_training.collect.planned_scenarios',return_value={'episodes':[item]}):
                with self.assertRaisesRegex(ValueError,'terminal record'):_collect_locked(bundle,destination,1,None,1,20,{},'fixture')
                self.assertFalse((destination/'manifest.json').exists())
                terminal['terminal']=True
                with h5py.File(episode/'observations.h5','r+') as data:data['steps'][-1]=json.dumps(terminal)
                with self.assertRaisesRegex(ValueError,'not aligned'):_collect_locked(bundle,destination,1,None,1,20,{},'fixture')
                (episode/'steps.jsonl').write_text(json.dumps(first)+'\n'+json.dumps(terminal)+'\n')
                with patch('landing_training.execution.iter_jobs',return_value=iter(())):
                    manifest=_collect_locked(bundle,destination,1,None,1,20,{},'fixture')
                self.assertEqual(len(manifest['episodes']),1)
                self.assertEqual(manifest['episodes'][0]['outcome'],'abort')
    def test_collection_and_review_have_identical_onboard_pixels(self):
        from .config import Scenario
        from .environment import Environment
        from .rendering import ReviewRenderer
        env=Environment(Scenario(kind='city',wave_height=.1,wave_period=4.5,world_rotation_deg=83))
        collector=ReviewRenderer(env,overview=False);review=ReviewRenderer(env)
        try:
            self.assertIsNone(collector.external)
            with patch.object(env.boat,'waves',wraps=env.boat.waves) as waves:
                _,expected=review.capture()
                self.assertEqual(waves.call_count,1)
            actual=collector.onboard_image()
            np.testing.assert_array_equal(actual,expected)
            self.assertIsNone(collector.external)
            # A changed clock must refresh the physical wave surface.
            env.data.time+=.04
            with patch.object(env.boat,'waves',wraps=env.boat.waves) as waves:
                review.capture();self.assertEqual(waves.call_count,1)
        finally:collector.close();review.close()

if __name__=='__main__':unittest.main()
