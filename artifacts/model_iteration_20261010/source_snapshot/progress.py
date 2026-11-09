"""Small durable training telemetry; no CUDA work or extra image reads."""
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import time
import uuid

from .collection_session import atomic_json


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_text(path, text):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='') as stream:
        stream.write(text); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)


def export_loss_history(output, history):
    """Committed epochs only; checkpoint history repairs exports after a crash."""
    fields = ('epoch', 'finished_utc', 'training_elapsed_hours', 'epoch_seconds',
              'optimizer_steps', 'train_lane_loss_mean', 'validation_loss',
              'validation_action_huber', 'persistence_action_huber')
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields); writer.writeheader()
    for row in history:
        metrics = row.get('validation_metrics', {})
        writer.writerow({**{field: row.get(field, '') for field in fields},
                         'validation_action_huber': metrics.get('action_huber', ''),
                         'persistence_action_huber': metrics.get('persistence_action_huber', '')})
    atomic_text(Path(output) / 'loss_history.csv', buffer.getvalue())
    atomic_json(Path(output) / 'history.json', history)


class TrainingProgress:
    def __init__(self, output, epochs, started=None):
        self.output = Path(output); self.started = time.monotonic() if started is None else started
        path = self.output / 'training_progress.json'
        previous = json.loads(path.read_text()) if path.exists() else {}
        self.prior_seconds = previous.get('elapsed_training_seconds', 0.)
        self.attempt = uuid.uuid4().hex
        self.state = {'schema': 'aerodock.landing.training_progress.v1',
                      'status': 'running', 'phase': 'dataset_integrity',
                      'epoch_budget': epochs, 'completed_epochs': 0,
                      'attempt': self.attempt}
        self.last_write = -float('inf'); self.save(force=True)

    def save(self, force=False, **values):
        self.state.update(values)
        now = time.monotonic()
        if not force and now - self.last_write < 5:
            return
        self.state.update(updated_utc=utc_now(),
                          elapsed_training_seconds=self.prior_seconds + now - self.started)
        atomic_json(self.output / 'training_progress.json', self.state)
        self.last_write = now

    def cache(self, **values):
        self.save(phase='feature_preparation', **values)

    def loss_sample(self, epoch, step, lanes, loss):
        """Attempt-labelled samples may include an epoch retried after interruption."""
        path = self.output / 'loss_updates.csv'
        fields = ('timestamp_utc', 'training_elapsed_hours', 'attempt', 'epoch',
                  'optimizer_step', 'window_lanes', 'train_lane_loss_mean')
        new = not path.exists() or path.stat().st_size == 0
        with path.open('a', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            if new: writer.writeheader()
            writer.writerow(dict(zip(fields, (utc_now(),
                (self.prior_seconds + time.monotonic() - self.started) / 3600,
                self.attempt, epoch, step, lanes, loss / max(1, lanes)))))
            stream.flush(); os.fsync(stream.fileno())
