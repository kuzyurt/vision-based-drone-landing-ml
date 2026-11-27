"""A small grid router for the FE-1 board (A* on two layers, 45-degree moves).

Good enough for a two-layer board of this size: nets are routed one after the
other, power nets first and wide, each as a tree that grows from its first pad.
Every obstacle is inflated by the clearance plus half the track width, so a
found path keeps the design rules. GND is not routed: it is the plane on both
layers, stitched with vias. Run DRC afterwards; this is no substitute for a
review of the power loops.
"""
from __future__ import annotations

import heapq
import math

import numpy as np
import pcbnew

GRID = 0.2          # mm
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_COST = 12.0
MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]


class Router:
    def __init__(self, board, width_mm, clearance=0.2, power_width=0.8, power_nets=()):
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

        for code, layers, (x1, y1, x2, y2), _ in self.copper:
            if code != net:
                mark(layers, x1, y1, x2, y2, (0.3 if code == -2 else self._gap(code, net)) + width / 2)
        for code, layer, x1, y1, x2, y2, w in self.tracks:
            if code != net:
                grow = self._gap(code, net) + width / 2 + w / 2
                steps = max(1, int(math.hypot(x2 - x1, y2 - y1) / (GRID / 2)))
                for k in range(steps + 1):
                    x, y = x1 + (x2 - x1) * k / steps, y1 + (y2 - y1) * k / steps
                    mark([layer], x, y, x, y, grow)
        for code, x, y in self.vias:
            if code != net:
                mark([0, 1], x, y, x, y, self._gap(code, net) + width / 2 + VIA_D / 2)
        return blocked

    def route_net(self, net_name, width=None):
        net = self.board.FindNet(net_name)
        code = net.GetNetCode()
        if width is None:
            width = self.power_width if net_name in self.power_nets else self.width
        pads = [(layers, bb, pad) for c, layers, bb, pad in self.copper if c == code]
        if len(pads) < 2:
            return True
        blocked = self._blocked(code, width)
        via_blocked = self._blocked(code, VIA_D)
        via_ok = ~(via_blocked[0] | via_blocked[1])

        def pad_cells(layers, bb):
            """Grid cells inside the pad where a track end of this width stays on the pad."""
            x1, y1, x2, y2 = bb
            m = min(width / 2, (x2 - x1) / 2 - 0.01, (y2 - y1) / 2 - 0.01)
            i1, j1 = self._cell(x1 + m, y1 + m)
            i2, j2 = self._cell(x2 - m, y2 - m)
            cells = {(layer, i, j) for layer in layers for i in range(i1, i2 + 1) for j in range(j1, j2 + 1)
                     if self.x0 + i * GRID >= x1 + m - 1e-6 and self.x0 + i * GRID <= x2 - m + 1e-6
                     and self.y0 + j * GRID >= y1 + m - 1e-6 and self.y0 + j * GRID <= y2 - m + 1e-6}
            if not cells:
                i, j = self._cell((x1 + x2) / 2, (y1 + y2) / 2)
                cells = {(layer, i, j) for layer in layers}
            return cells

        tree = set(pad_cells(*pads[0][:2]))
        for layer, i, j in tree:
            blocked[layer, i, j] = False
        remaining = pads[1:]
        ok = True
        while remaining:
            targets = {}
            for index, (layers, bb, _) in enumerate(remaining):
                for cell in pad_cells(layers, bb):
                    targets[cell] = index
                    blocked[cell[0], cell[1], cell[2]] = False
            path = self._astar(tree, targets, blocked, via_ok)
            if path is None:
                ok = False
                remaining.pop(0)
                continue
            index = targets[path[-1]]
            remaining.pop(index)
            self._commit(code, path, width)
            tree.update(path)
        return ok

    def _astar(self, sources, targets, blocked, via_ok):
        tlist = list(targets)

        def h(layer, i, j):
            return min(math.hypot(i - ti, j - tj) for _, ti, tj in tlist)

        frontier, came, cost = [], {}, {}
        for s in sources:
            cost[s] = 0.0
            heapq.heappush(frontier, (h(*s), 0.0, s))
            came[s] = None
        limit = 400000
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
            for di, dj, step in MOVES:
                ni, nj = i + di, j + dj
                if not (0 <= ni < self.nx and 0 <= nj < self.ny) or blocked[layer, ni, nj]:
                    continue
                if di and dj and (blocked[layer, i + di, j] or blocked[layer, i, j + dj]):
                    continue
                nxt = (layer, ni, nj)
                ng = g + step + (0.3 if layer == 1 else 0.0)
                if ng < cost.get(nxt, 1e18):
                    cost[nxt], came[nxt] = ng, cell
                    heapq.heappush(frontier, (ng + h(*nxt), ng, nxt))
            other = (1 - layer, i, j)
            if via_ok[i, j] and not blocked[other]:
                ng = g + VIA_COST
                if ng < cost.get(other, 1e18):
                    cost[other], came[other] = ng, cell
                    heapq.heappush(frontier, (ng + h(*other), ng, other))
        return None

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


def route(board, nets_in_order, power_nets, width=0.25, power_width=0.8, fallback=(0.5, 0.3, 0.2)):
    """Route each net; when a net cannot be completed, rip it up and retry narrower."""
    router = Router(board, width, clearance=0.16, power_width=power_width, power_nets=power_nets)
    failed = []
    for name in nets_in_order:
        code = board.FindNet(name).GetNetCode()
        widths = [None] + [w for w in fallback if w < (power_width if name in power_nets else width)]
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
