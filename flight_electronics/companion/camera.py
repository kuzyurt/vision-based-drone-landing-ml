"""Camera input on the Orange Pi 5: RTSP sub-stream -> hardware decode -> 640x360 RGB.

The D-80Pro sends H.264/H.265 over Ethernet (RTSP, port 554). On the RK3588S the
Rockchip MPP decoder (``mppvideodec``) and the RGA scaler keep the CPU free for
the controller. ``latency=0`` and ``drop=true`` keep only the newest frame.
"""
from __future__ import annotations

import time

from ..hardware import design as D


def gstreamer_pipeline(url: str = D.CAMERA['rtsp_sub'], width=640, height=360, hardware=True) -> str:
    decode = ('rtph264depay ! h264parse ! mppvideodec ! videoconvert'
              if hardware else 'rtph264depay ! h264parse ! avdec_h264 ! videoconvert')
    return (f'rtspsrc location={url} latency=0 protocols=udp drop-on-latency=true ! {decode} ! '
            f'videoscale ! video/x-raw,format=BGR,width={width},height={height} ! '
            'appsink drop=true max-buffers=1 sync=false')


class RtspCamera:
    """Newest-frame reader. Needs OpenCV built with GStreamer (Orange Pi OS images ship it)."""

    def __init__(self, url: str = D.CAMERA['rtsp_sub'], hardware=True):
        import cv2  # imported here so the simulation does not need OpenCV
        self.cv2 = cv2
        self.capture = cv2.VideoCapture(gstreamer_pipeline(url, hardware=hardware), cv2.CAP_GSTREAMER)
        if not self.capture.isOpened():
            raise RuntimeError(f'cannot open camera stream {url}')

    def read(self):
        """Return (rgb 360x640x3 uint8, receive_time_s) or (None, now)."""
        ok, frame = self.capture.read()
        now = time.monotonic()
        if not ok:
            return None, now
        return self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB), now

    def close(self):
        self.capture.release()
