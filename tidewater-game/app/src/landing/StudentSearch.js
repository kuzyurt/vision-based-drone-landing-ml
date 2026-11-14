// Decode the combined student ONNX search head.  This is a literal browser
// port of benchmark/policies/student/model.py::decode; keep the thresholds and
// evidence ordering aligned with the trained checkpoint.

const EVIDENCE = ['unknown_boat', 'target_or_similar', 'different_boat', 'target_boat'];
const HEIGHT = 45, WIDTH = 80;
const DEFAULT = {
  threshold: 0.36,
  maxObjects: 7,
  evidenceThreshold: 0.8,
  identityThreshold: 0.98,
  targetLikeThreshold: 0.6,
  targetIdentityThreshold: 0.85,
};

const sigmoid = value => value >= 0 ? 1 / (1 + Math.exp(-value)) : Math.exp(value) / (1 + Math.exp(value));

function softmax(logits, offset, count, stride = 1) {
  let maximum = -Infinity;
  for (let i = 0; i < count; i++) maximum = Math.max(maximum, logits[offset + i * stride]);
  let total = 0;
  const values = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    values[i] = Math.exp(logits[offset + i * stride] - maximum);
    total += values[i];
  }
  for (let i = 0; i < count; i++) values[i] /= total;
  return values;
}

// Weak heat-map peaks below the proposal threshold. A boat near the horizon
// (~90-100 m) peaks at only 0.06-0.25 but in the same place frame after frame;
// the policy accumulates these by direction (they are never boats on their
// own). The outermost heat cells are skipped: they carry edge artefacts.
export function weakSearchPeaks(search, proposals = [], {minimum = 0.07, maximum = 0.36, count = 5} = {}) {
  if (!search?.search_heat) return [];
  const heat = search.search_heat, offset = search.search_offset, out = [];
  for (let row = 1; row < HEIGHT - 1; row++) {
    for (let col = 1; col < WIDTH - 1; col++) {
      const value = sigmoid(heat[row * WIDTH + col]);
      if (value < minimum || value >= maximum) continue;
      let peak = true;
      for (let dy = -2; dy <= 2 && peak; dy++) for (let dx = -2; dx <= 2; dx++) {
        const y = row + dy, x = col + dx;
        if ((dx || dy) && y >= 0 && y < HEIGHT && x >= 0 && x < WIDTH && sigmoid(heat[y * WIDTH + x]) > value) { peak = false; break; }
      }
      if (!peak) continue;
      const px = (col + 0.5 + offset[row * WIDTH + col]) * 640 / WIDTH, py = (row + 0.5 + offset[HEIGHT * WIDTH + row * WIDTH + col]) * 360 / HEIGHT;
      if (proposals.some(item => (px - item.pixel[0]) ** 2 + (py - item.pixel[1]) ** 2 < 28 ** 2)) continue;
      out.push({pixel: [px, py], confidence: value, evidence: 'weak', identity_target_probability: 0, weak: true});
    }
  }
  return out.sort((a, b) => b.confidence - a.confidence).slice(0, count);
}

export function decodeStudentSearch(search, options = {}) {
  if (!search) return [];
  const heat = search.search_heat, offset = search.search_offset, evidence = search.search_evidence, identity = search.search_identity;
  if (!(heat instanceof Float32Array) || heat.length !== HEIGHT * WIDTH) throw new Error('Student search heat tensor has the wrong shape');
  if (!(offset instanceof Float32Array) || offset.length !== 2 * HEIGHT * WIDTH) throw new Error('Student search offset tensor has the wrong shape');
  if (!(evidence instanceof Float32Array) || evidence.length !== 4 * HEIGHT * WIDTH) throw new Error('Student search evidence tensor has the wrong shape');
  if (!(identity instanceof Float32Array) || identity.length !== 2 * HEIGHT * WIDTH) throw new Error('Student search identity tensor has the wrong shape');
  const c = {...DEFAULT, ...options};
  const threshold = Math.min(Number(c.proposal_threshold ?? c.threshold), 0.36);
  const scores = new Float32Array(HEIGHT * WIDTH);
  for (let row = 0; row < HEIGHT; row++) {
    for (let col = 0; col < WIDTH; col++) {
      const index = row * WIDTH + col;
      const value = sigmoid(heat[index]);
      if (value < threshold) continue;
      let maximum = true;
      for (let dy = -2; dy <= 2 && maximum; dy++) {
        const y = row + dy;
        if (y < 0 || y >= HEIGHT) continue;
        for (let dx = -2; dx <= 2; dx++) {
          const x = col + dx;
          if (x < 0 || x >= WIDTH) continue;
          if (sigmoid(heat[y * WIDTH + x]) > value) { maximum = false; break; }
        }
      }
      if (maximum) scores[index] = value;
    }
  }
  const indices = Array.from(scores).map((value, index) => [value, index]).filter(item => item[0] >= threshold).sort((a, b) => b[0] - a[0] || b[1] - a[1]).slice(0, Number(c.max_objects ?? DEFAULT.maxObjects) * 2);
  const items = [];
  for (const [confidence, index] of indices) {
    if (confidence < threshold) continue;
    const row = Math.floor(index / WIDTH), col = index % WIDTH;
    const offsetIndex = row * WIDTH + col;
    const px = Math.fround(Math.fround(Math.fround(col + 0.5 + offset[offsetIndex]) * 640) / WIDTH);
    const py = Math.fround(Math.fround(Math.fround(row + 0.5 + offset[HEIGHT * WIDTH + offsetIndex]) * 360) / HEIGHT);
    if (items.some(item => (px - item.pixel[0]) ** 2 + (py - item.pixel[1]) ** 2 < 28 ** 2)) continue;
    const ev = softmax(evidence, offsetIndex, 4, HEIGHT * WIDTH);
    const ident = softmax(identity, offsetIndex, 2, HEIGHT * WIDTH);
    let k = 0;
    for (let i = 1; i < 4; i++) if (ev[i] > ev[k]) k = i;
    let label = EVIDENCE[k];
    const targetLike = ev[1] + ev[3];
    if (ev[k] < Number(c.evidenceThreshold ?? DEFAULT.evidenceThreshold)) {
      if (targetLike >= Number(c.targetLikeThreshold ?? DEFAULT.targetLikeThreshold)) {
        label = ev[3] >= 0.42 && ident[1] >= 0.82 ? 'target_boat' : 'target_or_similar';
      } else {
        label = 'unknown_boat';
      }
    }
    if (label === 'target_boat' && ident[1] < Math.min(Number(c.identityThreshold ?? DEFAULT.identityThreshold), Number(c.targetIdentityThreshold ?? DEFAULT.targetIdentityThreshold))) label = 'target_or_similar';
    if (label === 'different_boat' && ident[0] < Number(c.identityThreshold ?? DEFAULT.identityThreshold)) label = 'unknown_boat';
    items.push({
      pixel: [px, py],
      confidence: Number(confidence),
      evidence: label,
      identity_target_probability: Number(ident[1]),
    });
    if (items.length >= Number(c.max_objects ?? DEFAULT.maxObjects)) break;
  }
  return items;
}
