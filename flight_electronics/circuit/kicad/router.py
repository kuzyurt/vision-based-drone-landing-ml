"""A small grid router for the FE-1 board (A* on two layers, 45-degree moves).

Good enough for a two-layer board of this size: nets are routed one after the
other, power nets first and wide, each as a tree that grows from its first pad.
The search pays for every bend (more for sharper ones), and each found path is
then pulled tight: corners are joined by the straightest free connection of at
most two segments (a straight run and a 45-degree run), so tracks come out as
few long straight pieces instead of a staircase.
Every obstacle is inflated by the clearance plus half the track width, so a
found path keeps the design rules. GND is not routed: it is the plane on both
layers, stitched with vias. Run DRC afterwards; this is no substitute for a
review of the power loops.
"""
from __future__ import annotations

import heapq
import os
import math

import numpy as np
import pcbnew

GRID = 0.1          # mm
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_COST = 12.0
NECK_WIDTHS = (0.8, 0.5, 0.3)                      # narrower steps for pads a wide track cannot reach
TURN_COST = {0: 0.0, 1: 0.8, 2: 2.0, 3: 6.0}      # by eighths of a turn: straight, 45, 90, 135 degrees
MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]


def _eighths(a, b):
    """Angle between two grid directions in eighths of a turn (0..4)."""
    angle = abs(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]))
    return min(3, int(round(angle / (math.pi / 4))))


class Router:
    def __init__(self, board, width_mm, clearance=0.2, power_width=0.8, power_nets=(), keepouts=(), net_widths=None):
        self.net_widths = dict(net_widths or {})   # per-net track width (mm); power_width otherwise
        self.keepouts = list(keepouts)       # (x1, y1, x2, y2) mm: board cut-outs, kept 0.5 mm clear
        self.board = board
        box = board.GetBoardEdgesBoundingBox()
        self.x0, self.y0 = pcbnew.ToMM(box.GetX()), pcbnew.ToMM(box.GetY())
        self.nx = int(pcbnew.ToMM(box.GetWidth()) / GRID) + 1
        self.ny = int(pcbnew.ToMM(box.GetHeight()) / GRID) + 1
        self.clearance = clearance
        self.width = width_mm
        self.power_width = power_width
        self.power_nets = set(power_nets)
        self.power_codes = {board.FindNet(n).GetNetCode() for n in power_nets if board.FindNet(n)}
        # owner[layer, x, y]: net code occupying the cell (with its own copper extent); -1 free
        self.copper = []    # (net, layer or None for both, polygon-ish bbox in mm, kind)
        self.tracks = []    # (net, layer, x1, y1, x2, y2, width)
        self.vias = []      # (net, x, y)
        self.existing_tracks, self.existing_vias = [], []
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                layers = []
                if pad.IsOnLayer(pcbnew.F_Cu):
                    layers.append(0)
                if pad.IsOnLayer(pcbnew.B_Cu):
                    layers.append(1)
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    layers = [0, 1]
                if not layers:
                    continue   # paste-only apertures carry no copper
                self.copper.append((pad.GetNetCode() if pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH else -2,
                                    layers, (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()),
                                             pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())), pad))

    def _cell(self, x, y):
        return int(round((x - self.x0) / GRID)), int(round((y - self.y0) / GRID))

    def _xy(self, i, j):
        return self.x0 + i * GRID, self.y0 + j * GRID

    def _gap(self, a, b):
        return 0.21 if (a in self.power_codes or b in self.power_codes) else self.clearance

    def _blocked(self, net, width):
        """Boolean grid [2, nx, ny]: cells a track of this width and net may not use."""
        blocked = np.zeros((2, self.nx, self.ny), bool)
        edge = int(math.ceil((0.5 + width / 2) / GRID))
        blocked[:, :edge, :] = blocked[:, -edge:, :] = True
        blocked[:, :, :edge] = blocked[:, :, -edge:] = True

        def mark(layers, x1, y1, x2, y2, grow):
            i1, j1 = self._cell(x1 - grow, y1 - grow)
            i2, j2 = self._cell(x2 + grow, y2 + grow)
            for layer in layers:
                blocked[layer, max(i1, 0):max(i2 + 1, 0), max(j1, 0):max(j2 + 1, 0)] = True

        for kx1, ky1, kx2, ky2 in self.keepouts:
            mark([0, 1], kx1, ky1, kx2, ky2, 0.5 + width / 2)
        for code, layers, (x1, y1, x2, y2), _ in self.copper:
            if code != net:
                mark(layers, x1, y1, x2, y2, (0.3 if code == -2 else self._gap(code, net)) + width / 2)
        for code, layer, x1, y1, x2, y2, w in self.tracks + self.existing_tracks:
            if code != net:
                grow = self._gap(code, net) + width / 2 + w / 2
                steps = max(1, int(math.hypot(x2 - x1, y2 - y1) / (GRID / 2)))
                for k in range(steps + 1):
                    x, y = x1 + (x2 - x1) * k / steps, y1 + (y2 - y1) * k / steps
                    mark([layer], x, y, x, y, grow)
        for code, x, y in self.vias + self.existing_vias:
            if code != net:
                mark([0, 1], x, y, x, y, self._gap(code, net) + width / 2 + VIA_D / 2)
        return blocked

    def route_net(self, net_name, width=None):
        net = self.board.FindNet(net_name)
        code = net.GetNetCode()
        if width is None:
            width = self.net_widths.get(net_name, self.power_width if net_name in self.power_nets else self.width)
        pads = [(layers, bb, pad) for c, layers, bb, pad in self.copper if c == code]
        if len(pads) < 2:
            return True
        # Each connection is tried at the net's width first; a pad the wide track cannot reach
        # (a fine-pitch IC pin) is joined with the widest narrower track that fits: the trunk
        # stays wide and only the last piece necks down.
        steps = [width] + [w for w in NECK_WIDTHS if w < width - 1e-9]
        grids = {}

        def grid(w):
            if w not in grids:
                grids[w] = self._blocked(code, w)
            return grids[w]
        via_blocked = self._blocked(code, VIA_D)
        via_ok = ~(via_blocked[0] | via_blocked[1])

        def pad_cells(layers, bb, pad=None):
            """Grid cells inside the pad where a track end of this width stays on the pad."""
            x1, y1, x2, y2 = bb
            m = min(width / 2, (x2 - x1) / 2 - 0.01, (y2 - y1) / 2 - 0.01)
            i1, j1 = self._cell(x1 + m, y1 + m)
            i2, j2 = self._cell(x2 - m, y2 - m)
            cells = {(layer, i, j) for layer in layers for i in range(i1, i2 + 1) for j in range(j1, j2 + 1)
                     if self.x0 + i * GRID >= x1 + m - 1e-6 and self.x0 + i * GRID <= x2 - m + 1e-6
                     and self.y0 + j * GRID >= y1 + m - 1e-6 and self.y0 + j * GRID <= y2 - m + 1e-6}
            if pad is not None:     # round and rotated pads: the cell centre must lie on the copper
                cells = {c for c in cells if pad.HitTest(pcbnew.VECTOR2I_MM(*self._xy(c[1], c[2])), 0)}
            if not cells:
                i, j = self._cell((x1 + x2) / 2, (y1 + y2) / 2)
                cells = {(layer, i, j) for layer in layers}
            return cells

        full = width
        tree = set(pad_cells(*pads[0][:3]))
        remaining = pads[1:]
        ok = True
        while remaining:
            path = None
            for width in steps:
                # only cells where a track of this width keeps clear of other nets: a wide track
                # may neither leave nor reach a fine-pitch pin, it necks down instead
                blocked = grid(width)
                sources = {c for c in tree if not blocked[c]}
                targets = {}
                for index, (layers, bb, pad) in enumerate(remaining):
                    for cell in pad_cells(layers, bb, pad):
                        if not blocked[cell]:
                            targets[cell] = index
                if not sources or not targets:
                    continue
                path = self._astar(sources, targets, blocked, via_ok)
                if path is not None:
                    break
            if path is None and os.environ.get('FE_ROUTE_DEBUG'):
                print('no path', net_name, full, 'sources', len(tree), 'targets', len(targets))
            if path is None:
                ok = False
                remaining.pop(0)
                continue
            index = targets[path[-1]]
            remaining.pop(index)
            path = self._tighten(path, blocked)
            self._commit(code, path, width)
            tree.update(path)
        return ok

    def _astar(self, sources, targets, blocked, via_ok):
        tlist = list(targets)

        def h(layer, i, j):
            return min(math.hypot(i - ti, j - tj) for _, ti, tj in tlist)

        frontier, came, cost, heading = [], {}, {}, {}
        weight = 1.3      # mildly greedy A*: much faster on long runs, paths stay near-shortest
        for s in sources:
            cost[s] = 0.0
            heapq.heappush(frontier, (weight * h(*s), 0.0, s))
            came[s] = None
            heading[s] = None
        limit = 2_000_000
        while frontier and limit:
            limit -= 1
            _, g, cell = heapq.heappop(frontier)
            if cell in targets:
                path = [cell]
                while came[path[-1]] is not None:
                    path.append(came[path[-1]])
                return path[::-1]
            if g > cost.get(cell, 1e18):
                continue
            layer, i, j = cell
            before = heading.get(cell)
            for k, (di, dj, step) in enumerate(MOVES):
                ni, nj = i + di, j + dj
                if not (0 <= ni < self.nx and 0 <= nj < self.ny) or blocked[layer, ni, nj]:
                    continue
                if di and dj and (blocked[layer, i + di, j] or blocked[layer, i, j + dj]):
                    continue
                nxt = (layer, ni, nj)
                turn = 0.0 if before is None else TURN_COST[_eighths(before, (di, dj))]
                ng = g + step + turn + (0.3 if layer == 1 else 0.0)
                if ng < cost.get(nxt, 1e18):
                    cost[nxt], came[nxt], heading[nxt] = ng, cell, (di, dj)
                    heapq.heappush(frontier, (ng + weight * h(*nxt), ng, nxt))
            other = (1 - layer, i, j)
            if via_ok[i, j] and not blocked[other]:
                ng = g + VIA_COST
                if ng < cost.get(other, 1e18):
                    cost[other], came[other], heading[other] = ng, cell, None
                    heapq.heappush(frontier, (ng + weight * h(*other), ng, other))
        return None

    def _line(self, layer, a, b, blocked):
        """Cells of the straight or 45-degree line a -> b (grid indices), or None if any is blocked."""
        (i1, j1), (i2, j2) = a, b
        di, dj = i2 - i1, j2 - j1
        n = max(abs(di), abs(dj))
        if n == 0:
            return [(layer, i1, j1)]
        if di and dj and abs(di) != abs(dj):
            return None
        si, sj = (di > 0) - (di < 0), (dj > 0) - (dj < 0)
        cells = [(layer, i1, j1)]
        i, j = i1, j1
        for _ in range(n):
            if si and sj and (blocked[layer, i + si, j] or blocked[layer, i, j + sj]):
                return None
            i, j = i + si, j + sj
            if blocked[layer, i, j]:
                return None
            cells.append((layer, i, j))
        return cells

    def _dogleg(self, layer, a, b, blocked):
        """a -> b as one straight / 45-degree line, or as a straight run plus a 45-degree run
        (either order); None if no such connection is free."""
        direct = self._line(layer, a, b, blocked)
        if direct is not None:
            return direct
        (i1, j1), (i2, j2) = a, b
        di, dj = i2 - i1, j2 - j1
        m = min(abs(di), abs(dj))
        si, sj = (di > 0) - (di < 0), (dj > 0) - (dj < 0)
        for corner in ((i1 + si * m, j1 + sj * m), (i2 - si * m, j2 - sj * m)):
            first = self._line(layer, a, corner, blocked)
            if first is None:
                continue
            second = self._line(layer, corner, b, blocked)
            if second is not None:
                return first + second[1:]
        return None

    def _tighten(self, path, blocked):
        """Pull a found path tight, layer run by layer run (the vias stay where they are)."""
        runs, current = [], [path[0]]
        for cell in path[1:]:
            if cell[0] != current[-1][0]:
                runs.append(current)
                current = [cell]
            else:
                current.append(cell)
        runs.append(current)
        out = []
        for run in runs:
            layer = run[0][0]
            corners = [0]
            for k in range(1, len(run) - 1):
                d1 = (run[k][1] - run[k - 1][1], run[k][2] - run[k - 1][2])
                d2 = (run[k + 1][1] - run[k][1], run[k + 1][2] - run[k][2])
                if d1 != d2:
                    corners.append(k)
            if len(run) > 1:
                corners.append(len(run) - 1)
            pts = [(run[k][1], run[k][2]) for k in corners]
            cells = [run[0]]
            i = 0
            while i < len(pts) - 1:
                for j in range(len(pts) - 1, i, -1):
                    seg = self._dogleg(layer, pts[i], pts[j], blocked)
                    if seg is not None:
                        cells += seg[1:]
                        i = j
                        break
                else:                       # cannot happen: neighbouring corners lie on one line
                    cells += [c for c in run[corners[i] + 1:corners[i + 1] + 1]]
                    i += 1
            out += cells
        return out

    def _commit(self, code, path, width):
        # collapse into straight runs per layer, add vias on layer changes
        runs, start = [], path[0]
        prev, direction = path[0], None
        for cell in path[1:]:
            if cell[0] != prev[0]:
                if prev != start:
                    runs.append((start, prev))
                self.vias.append((code, *self._xy(prev[1], prev[2])))
                start, prev, direction = cell, cell, None
                continue
            d = (cell[1] - prev[1], cell[2] - prev[2])
            if direction is not None and d != direction:
                runs.append((start, prev))
                start = prev
            direction = d
            prev = cell
        if prev != start:
            runs.append((start, prev))
        for (layer, i1, j1), (_, i2, j2) in runs:
            x1, y1 = self._xy(i1, j1)
            x2, y2 = self._xy(i2, j2)
            self.tracks.append((code, layer, x1, y1, x2, y2, width))

    def load_existing(self):
        """Treat the tracks and vias already on the board as obstacles (not re-added by apply())."""
        for t in self.board.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA):
                self.existing_vias.append((t.GetNetCode(), pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)))
            else:
                layer = 0 if t.GetLayer() == pcbnew.F_Cu else 1
                self.existing_tracks.append((t.GetNetCode(), layer, pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y),
                                             pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y), pcbnew.ToMM(t.GetWidth())))

    def drop_to_plane(self, net_name, pad, width=0.3):
        """Short top-layer track from an SMD pad to the nearest spot where a via fits (the via
        joins the bottom ground plane), or to the nearest other pad of the same net, whichever
        comes first."""
        code = self.board.FindNet(net_name).GetNetCode()
        key = lambda p: (p.GetParentFootprint().GetReference(), p.GetNumber())   # SWIG wrappers differ per access
        others = [bb for c, layers, bb, p in self.copper if c == code and 0 in layers and key(p) != key(pad)]
        blocked = self._blocked(code, width)
        via_blocked = self._blocked(code, VIA_D)
        bb = pad.GetBoundingBox()
        i, j = self._cell(pcbnew.ToMM(bb.Centre().x), pcbnew.ToMM(bb.Centre().y))
        start = (0, i, j)
        frontier, came, seen = [(0.0, start)], {start: None}, {start}
        while frontier:
            g, cell = heapq.heappop(frontier)
            layer, ci, cj = cell
            far = math.hypot(ci - i, cj - j) * GRID
            x, y = self._xy(ci, cj)
            if far > 0.3 and any(x1 + 0.15 <= x <= x2 - 0.15 and y1 + 0.15 <= y <= y2 - 0.15 for x1, y1, x2, y2 in others):
                path = [cell]
                while came[path[-1]] is not None:
                    path.append(came[path[-1]])
                self._commit(code, path[::-1], width)
                return True
            if far > 0.9 and not via_blocked[0, ci, cj] and not via_blocked[1, ci, cj]:
                path = [cell]
                while came[path[-1]] is not None:
                    path.append(came[path[-1]])
                path = path[::-1]
                self._commit(code, path, width)
                self.vias.append((code, *self._xy(ci, cj)))
                return True
            for di, dj, step in MOVES:
                ni, nj = ci + di, cj + dj
                nxt = (0, ni, nj)
                if 0 <= ni < self.nx and 0 <= nj < self.ny and nxt not in seen and not blocked[0, ni, nj]:
                    seen.add(nxt)
                    came[nxt] = cell
                    heapq.heappush(frontier, (g + step, nxt))
        return False

    def apply(self):
        for code, layer, x1, y1, x2, y2, w in self.tracks:
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(pcbnew.VECTOR2I_MM(x1, y1))
            t.SetEnd(pcbnew.VECTOR2I_MM(x2, y2))
            t.SetWidth(pcbnew.FromMM(w))
            t.SetLayer(pcbnew.F_Cu if layer == 0 else pcbnew.B_Cu)
            t.SetNetCode(code)
            self.board.Add(t)
        for code, x, y in self.vias:
            v = pcbnew.PCB_VIA(self.board)
            v.SetPosition(pcbnew.VECTOR2I_MM(x, y))
            v.SetWidth(pcbnew.FromMM(VIA_D))
            v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetNetCode(code)
            self.board.Add(v)


def route(board, nets_in_order, power_nets, width=0.25, power_width=0.8, fallback=(0.5, 0.3, 0.2), keepouts=(),
          net_widths=None, pre_drop=()):
    """Route each net; when a net cannot be completed, rip it up and retry narrower."""
    router = Router(board, width, clearance=0.16, power_width=power_width, power_nets=power_nets, keepouts=keepouts,
                    net_widths=net_widths)
    for net, pad in pre_drop:          # ground vias of decoupling capacitors first, right at their pads
        router.drop_to_plane(net, pad)
    failed = []
    for name in nets_in_order:
        own = (net_widths or {}).get(name, power_width if name in power_nets else width)
        widths = [None] + [w for w in fallback if w < own]
        for w in widths:
            tracks, vias = len(router.tracks), len(router.vias)
            if router.route_net(name, w):
                break
            del router.tracks[tracks:]
            del router.vias[vias:]
        else:
            failed.append(name)
    router.apply()
    return failed
