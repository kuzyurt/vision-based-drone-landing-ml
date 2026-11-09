"""Bounded exact caches for the frozen calibrated camera transform.

Retains the reference matrix multiplication order and unrounded encoder angles.
Only the latest prefix at each chain step is retained; no flight history grows.
"""
import math
import numpy as np

_calibration = None
_steps = []
_keys = []
_prefixes = []


def _prepare(calibration):
    global _calibration, _steps, _keys, _prefixes
    from .camera_geometry import quaternion_matrix, transform
    steps = []
    for body in calibration['camera_chain']:
        steps.append(('static', transform(quaternion_matrix(body['quat']), body['pos'])))
        for joint in body['joints']:
            steps.append(('static', transform(position=joint['pos'])))
            axis = np.asarray(joint['axis'], dtype=float)
            axis = axis / np.linalg.norm(axis)
            cross = np.array([[0, -axis[2], axis[1]],
                              [axis[2], 0, -axis[0]],
                              [-axis[1], axis[0], 0]])
            steps.append(('joint', joint['encoder_index'], joint['reference'], cross, cross @ cross))
            steps.append(('static', transform(position=-np.array(joint['pos']))))
    steps.append(('static', transform(quaternion_matrix(calibration['camera_quat']), calibration['camera_pos'])))
    _calibration, _steps = calibration, steps
    _keys = [None] * len(steps)
    _prefixes = [None] * len(steps)


def camera_body_transform_fast(calibration, gimbal):
    if _calibration is not calibration:
        _prepare(calibration)
    dependencies = ()
    result = np.eye(4)
    for index, step in enumerate(_steps):
        if step[0] == 'joint':
            angle = float(gimbal[step[1]]) - step[2]
            dependencies += (angle,)
        if _keys[index] == dependencies:
            result = _prefixes[index]
            continue
        if step[0] == 'static':
            matrix = step[1]
        else:
            matrix = np.eye(4)
            matrix[:3, :3] = np.eye(3) + math.sin(angle) * step[3] + (1 - math.cos(angle)) * step[4]
        result = result @ matrix
        _keys[index], _prefixes[index] = dependencies, result
    # The reference returns a fresh writable matrix, never shared cache storage.
    return result.copy()
