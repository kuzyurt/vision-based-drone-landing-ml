"""Check adaptive choices, GPU detection and resource-budget cancellation."""
import json
import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from .autotune import best_result,initial_worker_cap,probe_backends,refinement_counts,prune_recordings,main,requested_worker_counts,TrialStopped
from .resource_monitor import GIB,ResourceMonitor,nvidia_snapshot,renderer_gpu_indices

def result(count,speed):return {'workers':count,'complete_episode_pipeline_per_hour':speed}

class AutoTuneChecks(unittest.TestCase):
    def test_requested_counts_do_not_insert_baseline(self):
        import argparse
        self.assertEqual(requested_worker_counts('64,32,64'),[32,64])
        for value in ('','0,32','32,129','32,no'):
            with self.subTest(value=value),self.assertRaises(argparse.ArgumentTypeError):requested_worker_counts(value)
    def test_fixed_counts_skip_search_and_preserve_resource_stops(self):
        for resource_stop in (False,True):
            with self.subTest(resource_stop=resource_stop):
                tested=[]
                def fake_trial(count,cases,repeats,phase,*args):
                    tested.append((phase,count))
                    if resource_stop and count==64:raise TrialStopped('process-tree RAM budget exceeded')
                    return dict(result(count,100 if count==32 else 90),phase=phase,recording_fps=100,
                        max_worker_ram_MiB=1024,resources=[],mean_used_cpu_cores=30,
                        peak_used_cpu_cores_sampled=32,peak_ram_GiB=count,
                        peak_device_vram_GiB=None,gpu_rendering_used=True,projected_collection_hours=10)
                graphics={'renderer':'NVIDIA L4','backend':'egl','software_rendering':False}
                with tempfile.TemporaryDirectory() as folder,contextlib.ExitStack() as stack:
                    output=Path(folder)/'run'
                    patches=[patch('landing_training.autotune.run_trial',side_effect=fake_trial),
                        patch('landing_training.autotune.probe_backends',return_value=(graphics,[])),
                        patch('landing_training.autotune.available_memory',return_value=128*GIB),
                        patch('landing_training.autotune.cpu_topology',return_value={}),
                        patch('landing_training.autotune.nvidia_snapshot',return_value=([],None)),
                        patch('landing_training.collection_benchmark.hardware_info',return_value={'effective_cpu_capacity':32,'ram_GiB':128}),
                        patch('landing_training.collection_benchmark.benchmark_scenarios',return_value=[{}]),
                        patch('landing_training.autotune.check_px4'),
                        patch('landing_training.autotune.cache_lock',return_value=contextlib.nullcontext()),
                        patch('landing_training.scene.compile_scene',return_value=object()),
                        patch('landing_training.gate.source_fingerprint',return_value='fixture')]
                    for p in patches:stack.enter_context(p)
                    stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                    self.assertEqual(main(['--worker-counts','32,64','--confirm-scenarios','1','--output',str(output)]),0)
                    report=json.loads((output/'report.json').read_text())
                    self.assertEqual(tested,[('confirm',32),('confirm',64)])
                    self.assertEqual(report['search_mode'],'fixed_full_flights')
                    self.assertEqual(report['probe_scenarios'],[])
                    self.assertEqual(report['recommendation']['workers'],32)
                    self.assertEqual(report['status'],'stopped' if resource_stop else 'completed')
                    if resource_stop:self.assertEqual(report['stopped_trials'][0]['workers'],64)
    def test_choose_lower_concurrency_inside_noise_margin(self):
        rows=[result(1,50),result(2,98),result(4,100)]
        self.assertEqual(best_result(rows)['workers'],2)
        self.assertEqual(best_result(rows,0.)['workers'],4)
    def test_refine_around_peak_without_retesting_counts(self):
        rows=[result(1,10),result(2,20),result(4,40),result(8,35),result(16,30)]
        self.assertEqual(refinement_counts(rows,16),[3,5,6])
        rows += [result(3,30),result(5,45),result(6,50)]
        self.assertEqual(refinement_counts(rows,16),[7])
        rows += [result(7,47)]
        self.assertEqual(refinement_counts(rows,16),[])
    def test_worker_cap_uses_allocation_and_ram_not_host_core_count(self):
        with patch('landing_training.autotune.available_memory',return_value=32*GIB):
            self.assertEqual(initial_worker_cap({'effective_cpu_capacity':4},None,20),4)
        with patch('landing_training.autotune.available_memory',return_value=4*GIB):
            self.assertEqual(initial_worker_cap({'effective_cpu_capacity':64},None,20),1)
    def test_gpu_inventory_preserves_unknown_metrics(self):
        output='0, GPU-123, NVIDIA RTX A4000, 16384, 1024, 15360, N/A, N/A, 580.0\n'
        with patch('landing_training.resource_monitor.shutil.which',return_value='nvidia-smi'),patch('landing_training.resource_monitor.subprocess.run',return_value=subprocess.CompletedProcess([],0,output,'')):
            devices,error=nvidia_snapshot()
        self.assertIsNone(error);self.assertIsNone(devices[0]['gpu_utilization_percent'])
        self.assertEqual(devices[0]['vram_used_MiB'],1024)
        self.assertEqual(renderer_gpu_indices('NVIDIA RTX A4000/PCIe/SSE2',devices),[0])
        self.assertEqual(renderer_gpu_indices('NVIDIA RTX A4000',devices+[dict(devices[0],index=1)]),[])
    def test_hardware_backend_preferred_over_software(self):
        cpu={'renderer':'llvmpipe','backend':'egl','software_rendering':True}
        gpu={'renderer':'NVIDIA RTX A4000','backend':'glfw','software_rendering':False}
        responses=[subprocess.CompletedProcess([],0,json.dumps(cpu),''),subprocess.CompletedProcess([],0,json.dumps(gpu),''),subprocess.CompletedProcess([],1,'','unavailable')]
        with patch.dict(os.environ,{'DISPLAY':':99'}),patch('landing_training.autotune.WINDOWS',False),patch('landing_training.autotune.subprocess.run',side_effect=responses):
            selected,probes=probe_backends()
        self.assertEqual(selected,gpu);self.assertEqual(len(probes),3)
    def test_software_gpu_translation_layers_are_not_acceleration(self):
        from .collection_benchmark import software_renderer
        self.assertTrue(software_renderer('zink Vulkan 1.3 (lavapipe)'))
        self.assertTrue(software_renderer('Microsoft Basic Render Driver'))
        self.assertFalse(software_renderer('D3D12 (NVIDIA GeForce RTX 2060)'))
        self.assertFalse(software_renderer('Mesa Intel(R) UHD Graphics'))
    def test_time_budget_requests_cooperative_cancellation(self):
        cancel=threading.Event()
        with patch('landing_training.resource_monitor.available_memory',return_value=32*GIB),patch('landing_training.resource_monitor.nvidia_snapshot',return_value=([],None)):
            with ResourceMonitor(cancel,ram_budget_bytes=64*GIB,reserve_bytes=GIB,deadline=time.monotonic()-1) as monitor:
                self.assertTrue(cancel.is_set())
        self.assertEqual(monitor.reason,'tuning time budget reached')
    def test_ram_guard_does_not_treat_device_detection_as_gpu_usage(self):
        cancel=threading.Event()
        with patch('landing_training.resource_monitor.available_memory',return_value=0),patch('landing_training.resource_monitor.nvidia_snapshot',return_value=([],None)):
            with ResourceMonitor(cancel,ram_budget_bytes=64*GIB,reserve_bytes=GIB,deadline=time.monotonic()+10) as monitor:pass
        self.assertEqual(monitor.reason,'available RAM fell below reserved headroom')
        self.assertEqual(monitor.report()['gpus'],[])
    def test_cleanup_only_removes_owned_raw_recordings(self):
        with tempfile.TemporaryDirectory() as folder:
            batch=Path(folder)/'batch';batch.mkdir();episode=batch/'worker_000';episode.mkdir()
            for name in ('observations.h5','steps.jsonl','summary.json','scenario.json'):(episode/name).write_text('fixture')
            unrelated=Path(folder)/'unrelated.h5';unrelated.write_text('retain')
            prune_recordings(batch)
            self.assertFalse((episode/'observations.h5').exists());self.assertFalse((episode/'steps.jsonl').exists())
            self.assertTrue((episode/'summary.json').exists());self.assertTrue(unrelated.exists())
    def test_end_to_end_search_finds_non_power_of_two_peak(self):
        tested=[];speeds={1:10,2:20,3:30,4:40,5:45,6:50,7:47,8:35}
        def fake_trial(count,cases,repeats,phase,*args):
            tested.append((phase,count))
            return dict(result(count,speeds[count]),phase=phase,recording_fps=speeds[count],
                max_worker_ram_MiB=1024,resources=[],mean_used_cpu_cores=count,
                peak_used_cpu_cores_sampled=count,peak_ram_GiB=count,
                peak_device_vram_GiB=None,gpu_rendering_used=True,
                projected_collection_hours=10 if phase=='confirm' else None)
        hardware={'effective_cpu_capacity':8,'ram_GiB':32}
        graphics={'renderer':'NVIDIA RTX A4000','backend':'egl','software_rendering':False}
        with tempfile.TemporaryDirectory() as folder,contextlib.ExitStack() as stack:
            output=Path(folder)/'run'
            patches=[patch('landing_training.autotune.run_trial',side_effect=fake_trial),
                patch('landing_training.autotune.probe_backends',return_value=(graphics,[])),
                patch('landing_training.autotune.available_memory',return_value=64*GIB),
                patch('landing_training.autotune.cpu_topology',return_value={}),
                patch('landing_training.autotune.nvidia_snapshot',return_value=([],None)),
                patch('landing_training.collection_benchmark.hardware_info',return_value=hardware),
                patch('landing_training.collection_benchmark.benchmark_scenarios',return_value=[{}]),
                patch('landing_training.autotune.check_px4'),
                patch('landing_training.autotune.cache_lock',return_value=contextlib.nullcontext()),
                patch('landing_training.scene.compile_scene',return_value=object()),
                patch('landing_training.gate.source_fingerprint',return_value='fixture')]
            for p in patches:stack.enter_context(p)
            self.assertEqual(main(['--max-workers','8','--confirm-scenarios','1','--output',str(output)]),0)
            recommendation=json.loads((output/'recommended_configuration.json').read_text())
            self.assertEqual(recommendation['workers'],6)
            self.assertIn(('probe',7),tested)
            self.assertEqual(len(tested),len(set(tested)))
            self.assertEqual({n for phase,n in tested if phase=='confirm'},{6,7})

if __name__=='__main__':unittest.main()
