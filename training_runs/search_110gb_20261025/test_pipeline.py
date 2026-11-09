"""Safety/data/transfer contract tests. Synthetic test records are not datasets."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import numpy as np
import torch
from common import check_no_radio, make_plan, no_radio_observation, config
from collect import reserve_fits
from storage import EpisodeWriter, open_read, read_frame, pack_rgb, unpack_rgb
from model import targets, loss, SearchHead, load_backbone, encode_maps, decode
from wake_collect import choose_workers


class PipelineTests(unittest.TestCase):
    def test_byte_exact_storage_random_and_renderlike_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'episode.sqlite'
            w=EpisodeWriter(path,dict(test_only=True))
            random=np.random.default_rng(4).integers(0,256,(360,640,3),dtype=np.uint8)
            flat=np.full((360,640,3),128,dtype=np.uint8)
            for a in (random,flat):w.append(a,dict(observation={},supervision={'boats':[]}))
            result=w.finish(dict(condition_valid=True))
            self.assertEqual(result['frames'],2)
            db=open_read(path)
            try:
                for i,a in enumerate((random,flat)):
                    b,_=read_frame(db,i);self.assertTrue(np.array_equal(a,b))
            finally:db.close()
            self.assertEqual(pack_rgb(random)[0],'raw')
            self.assertLess(len(pack_rgb(flat)[1]),flat.nbytes)

    def test_decode_detects_pixel_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'episode.sqlite';w=EpisodeWriter(path,{})
            w.append(np.zeros((360,640,3),np.uint8),{})
            w.finish(dict(condition_valid=True))
            db=sqlite3.connect(path);db.execute('UPDATE frames SET rgb_sha=?',(b'0'*32,));db.commit();db.close()
            db=open_read(path)
            try:
                with self.assertRaisesRegex(ValueError,'checksum'):read_frame(db,0)
            finally:db.close()

    def test_parallel_reservations_and_real_free_space(self):
        self.assertTrue(reserve_fits(20,20,100,50,100,5))
        self.assertFalse(reserve_fits(20,40,100,50,100,5))
        self.assertFalse(reserve_fits(0,10,100,50,60,5))

    def test_wakeup_ram_selection(self):
        c=dict(minimum_free_ram_bytes=2000000000,worker_ram_estimate_bytes=750000000,worker_ram_headroom_bytes=500000000)
        self.assertEqual(choose_workers(1900000000,c),0)
        self.assertEqual(choose_workers(2000000000,c),2)
        self.assertEqual(choose_workers(3000000000,c),3)

    def test_runtime_bundle_uses_sensors_and_returns_finite_action(self):
        import shutil
        from common import weight_path,sha,write_json
        from runtime import SearchRuntime
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp);(bundle/'base').mkdir()
            shutil.copy2(weight_path('pose'),bundle/'base/pose.pt')
            shutil.copy2(weight_path('spatial'),bundle/'base/spatial_acquisition.pt')
            c=config();head=SearchHead()
            torch.save(dict(schema='drone.search.transfer_head.v1',model=head.state_dict(),
                pose_sha256=c['pose_sha256'],spatial_sha256=c['spatial_sha256']),bundle/'search_best.pt')
            write_json(bundle/'policy.json',dict(checkpoint='search_best.pt',checkpoint_sha256=sha(bundle/'search_best.pt')))
            actor=SearchRuntime(bundle)
            own=dict(valid=True,position_enu_m=[0.,0.,6.],velocity_enu_m_s=[0.,0.,0.],
                attitude_ned_rad=[0.,0.,0.],angular_rate_frd_rad_s=[0.,0.,0.],
                position_age_s=0.,attitude_age_s=0.,armed=True,landed=False)
            obs=no_radio_observation(own,[0.,.1],[0.]*6,0.,0.,240.)
            action,diag=actor.act(np.zeros((360,640,3),np.uint8),obs)
            self.assertEqual(action.shape,(6,));self.assertTrue(np.isfinite(action).all())
            self.assertFalse(diag['boat_radio'])
            with self.assertRaises(ValueError):actor.act(np.zeros((360,640,3),np.uint8),obs|{'beacon':{}})

    def test_plan_fresh_roles_and_distribution(self):
        from collections import Counter
        plan=make_plan()
        self.assertEqual(Counter(e['role'] for e in plan),dict(training=48,validation=6,test=6))
        self.assertEqual(Counter(e['scenario']['distance'] for e in plan),{60.:6,80.:18,100.:36})
        self.assertEqual(set(Counter(e['scenario']['kind'] for e in plan).values()),{12})
        self.assertEqual(set(Counter(e['weather_level'] for e in plan).values()),{20})
        self.assertEqual(len({e['scenario']['world_seed'] for e in plan}),60)
        self.assertTrue(all(not e['scenario']['initial_camera_target'] for e in plan))

    def test_input_allowlist_rejects_truth_and_any_radio(self):
        obs=no_radio_observation(dict(valid=True,hidden_target=[1,2,3]),[0.,0.],[0.]*6,0.,0.,240.)
        check_no_radio(obs);self.assertNotIn('hidden_target',obs['px4'])
        for poison in ({'beacon':{'valid':False}},{'privileged':{}}):
            with self.assertRaises(ValueError):check_no_radio(obs|poison)
        obs['mission']['pad_position_enu_m']=[1,2,3]
        with self.assertRaises(ValueError):check_no_radio(obs)

    def test_unknown_identity_is_masked_tiny_instances_ignored(self):
        boat=dict(bbox=[100,80,140,120],boat_detection_valid=True,
                  evidence='unknown_boat',identity_supervision_valid=False)
        target=targets([boat])
        self.assertTrue((target['heat']==1).any())
        self.assertTrue((target['identity']==-100).all())
        tiny=dict(boat,bbox=[200,100,204,104],boat_detection_valid=False)
        target=targets([tiny]);self.assertFalse((target['heat']==1).any());self.assertTrue(target['ignore'].any())

    def test_conflicting_instance_identities_not_trained(self):
        a=dict(bbox=[100,80,140,120],boat_detection_valid=True,
               evidence='target_boat',identity_supervision_valid=True)
        b=dict(a,evidence='different_boat')
        target=targets([a,b]);self.assertTrue((target['identity']==-100).all())

    def test_transfer_optimizer_changes_head_only_and_roundtrips(self):
        torch.set_num_threads(1);torch.manual_seed(7)
        base=load_backbone();head=SearchHead()
        before={k:v.clone() for k,v in base.state_dict().items()}
        fine,context=encode_maps(base,torch.zeros(1,3,360,640,dtype=torch.uint8))
        target={k:v[None] for k,v in targets([]).items()}
        optimizer=torch.optim.AdamW(head.parameters(),lr=.001)
        prior=head.spatial.heat.bias.detach().clone()
        value,_=loss(head(fine,context),target);self.assertTrue(torch.isfinite(value))
        optimizer.zero_grad();value.backward();optimizer.step()
        self.assertFalse(torch.equal(prior,head.spatial.heat.bias))
        self.assertTrue(all(torch.equal(before[k],v) for k,v in base.state_dict().items()))
        self.assertTrue(all(p.grad is None for p in base.parameters()))
        output=head(fine,context);self.assertEqual(len(decode(output)),1)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'search.pt';torch.save(head.state_dict(),path)
            restored=SearchHead(initialize=False);restored.load_state_dict(torch.load(path,weights_only=True),strict=True)
            self.assertTrue(all(torch.equal(v,restored.state_dict()[k]) for k,v in head.state_dict().items()))

    def test_streamed_sqlite_training_and_validation_epoch(self):
        from train import Frames,epoch,parameter_hash
        from torch.utils.data import DataLoader
        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);writer=EpisodeWriter(root/'test.sqlite',dict(synthetic_unit_test=True))
            boat=dict(bbox=[300,160,340,200],boat_detection_valid=True,
                evidence='target_boat',identity_supervision_valid=True)
            writer.append(np.full((360,640,3),100,np.uint8),dict(supervision={'boats':[boat]}))
            writer.append(np.zeros((360,640,3),np.uint8),dict(supervision={'boats':[]}))
            writer.finish(dict(condition_valid=True))
            frames=Frames(root,[dict(database='test.sqlite',frames=2)])
            base=load_backbone();head=SearchHead();before=parameter_hash(base)
            optimizer=torch.optim.AdamW(head.parameters(),lr=.001)
            try:
                training=epoch(head,base,DataLoader(frames,batch_size=2),'cpu',optimizer)
                validation=epoch(head,base,DataLoader(frames,batch_size=2),'cpu')
            finally:frames.close()
            self.assertEqual(training['frames'],2);self.assertEqual(validation['frames'],2)
            self.assertTrue(np.isfinite(training['total']));self.assertEqual(before,parameter_hash(base))


if __name__=='__main__':unittest.main(verbosity=2)
