"""A pose graph of keyframes on the shelf plane.

Node i is the homography G_i of keyframe i into the map; the map is the plane of keyframe
0, whose pose stays fixed. Edge (i, j, T) is a measured homography T of keyframe j into
keyframe i: the chain of motions from one keyframe to the next (odometry), or a direct
registration of two keyframes' views (loop). The optimisation moves the nodes so that
G_i @ T and G_j agree on a grid of points of keyframe j, with a robust loss. A loop
closure then spreads the drift over the whole path, instead of leaving two copies of a
place in the map.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

from .homography import project


@dataclass
class Edge:
    i: int
    j: int
    T: np.ndarray                    # keyframe j -> keyframe i
    weight: float = 1.0
    kind: str = "odometry"           # odometry | loop


class PoseGraph:
    def __init__(self, size: tuple[int, int], grid: int = 3, loss_scale: float = 20.0,
                 stiffness: float = 3000.0):
        self.size = size
        xs = np.linspace(0.1, 0.9, grid) * size[0]
        ys = np.linspace(0.1, 0.9, grid) * size[1]
        self.grid = np.array([[x, y] for x in xs for y in ys], np.float64)
        self.loss_scale = loss_scale          # map pixels: the scale of the robust loss
        # Map pixels per unit of a change of the scale, rotation, shear, and perspective of
        # a node. The chain gets the shape of each keyframe right and its place wrong; with
        # no price on shape, a long chain bends its scale and perspective to pay off a loop.
        # The real chain drifts in scale too, so the shape MAY still move a little.
        self.stiffness = stiffness
        self.poses: list[np.ndarray] = []
        self.edges: list[Edge] = []
        # Keyframe pixels -> about [-1, 1]: the corrections are well scaled there.
        w, h = size
        self._norm = np.array([[2 / w, 0, -1], [0, 2 / w, -h / w], [0, 0, 1]], np.float64)

    def add(self, G: np.ndarray) -> int:
        self.poses.append(G / G[2, 2])
        return len(self.poses) - 1

    def connect(self, i: int, j: int, T: np.ndarray, weight: float = 1.0,
                kind: str = "odometry") -> Edge:
        edge = Edge(i, j, T / T[2, 2], weight, kind)
        self.edges.append(edge)
        return edge

    def replace(self, edge: Edge) -> Edge:
        """Add a loop or chain edge, replacing the earlier one of the same pair and kind:
        a pair registered again and again keeps one measurement, the latest."""
        pair = {edge.i, edge.j}
        self.edges = [e for e in self.edges
                      if not (e.kind == edge.kind and {e.i, e.j} == pair)]
        self.edges.append(edge)
        return edge

    def error(self, edge: Edge) -> float:
        """The largest disagreement of an edge with the poses, in map pixels."""
        a = project(self.poses[edge.i] @ edge.T, self.grid)
        b = project(self.poses[edge.j], self.grid)
        return float(np.linalg.norm(a - b, axis=1).max())

    def optimize_robust(self, outlier: float = 150.0, rounds: int = 3) -> tuple[float, float, int]:
        """Optimise, drop the loop edges that still disagree by more than `outlier` map
        pixels (a false registration: the robust loss keeps it from bending the graph much,
        but not from bending it at all), and optimise again. Odometry edges stay: they
        hold the graph together. Return (error before, error after, dropped edges)."""
        before, after = self.optimize()
        dropped = 0
        for _ in range(rounds):
            bad = [e for e in self.edges if e.kind != "odometry" and self.error(e) > outlier]
            if not bad:
                break
            worst = max(bad, key=self.error)
            # By identity: `list.remove` compares edges field by field, and two edges of one
            # pair of keyframes reach their homographies, which an array comparison cannot
            # decide.
            self.edges = [e for e in self.edges if e is not worst]
            dropped += 1
            _, after = self.optimize()
        return before, after, dropped

    def optimize(self, max_nfev: int = 50) -> tuple[float, float]:
        """Move the poses (all but the first) to agree with the edges. Return the largest
        edge error before and after, in map pixels."""
        n = len(self.poses)
        if n < 2 or not self.edges:
            return 0.0, 0.0
        before = max(self.error(e) for e in self.edges)
        start = [p.copy() for p in self.poses]
        norm, inv_norm = self._norm, np.linalg.inv(self._norm)
        grid_h = np.c_[self.grid, np.ones(len(self.grid))]
        mapped = [np.c_[project(e.T, self.grid), np.ones(len(self.grid))] for e in self.edges]

        def pose(x, node):
            if node == 0:
                return start[0]
            d = x[8 * (node - 1): 8 * node]
            D = np.array([[1 + d[0], d[1], d[2]], [d[3], 1 + d[4], d[5]], [d[6], d[7], 1.0]])
            return start[node] @ inv_norm @ D @ norm

        shape = np.array([0, 1, 3, 4, 6, 7])   # the corrections other than the shift

        def residuals(x):
            out = []
            for edge, points_i in zip(self.edges, mapped):
                a = points_i @ pose(x, edge.i).T
                b = grid_h @ pose(x, edge.j).T
                r = a[:, :2] / a[:, 2:3] - b[:, :2] / b[:, 2:3]
                out.append(r.ravel() * np.sqrt(edge.weight))
            out.append(self.stiffness * x.reshape(-1, 8)[:, shape].ravel())
            return np.concatenate(out)

        rows = 2 * len(self.grid)
        prior = len(shape) * (n - 1)
        sparsity = lil_matrix((rows * len(self.edges) + prior, 8 * (n - 1)), dtype=int)
        for k, edge in enumerate(self.edges):
            for node in (edge.i, edge.j):
                if node:
                    sparsity[k * rows:(k + 1) * rows, 8 * (node - 1):8 * node] = 1
        base = rows * len(self.edges)
        for node in range(n - 1):
            for k, column in enumerate(shape):
                sparsity[base + len(shape) * node + k, 8 * node + column] = 1
        result = least_squares(residuals, np.zeros(8 * (n - 1)), jac_sparsity=sparsity,
                               loss="soft_l1", f_scale=self.loss_scale, max_nfev=max_nfev)
        self.poses = [pose(result.x, node) for node in range(n)]
        self.poses = [p / p[2, 2] for p in self.poses]
        return before, max(self.error(e) for e in self.edges)
