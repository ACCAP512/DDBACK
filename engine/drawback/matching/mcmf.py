"""Exact integer min-cost flow primitive (DECISIONS D-004).

Successive-shortest-paths with Johnson potentials: a one-time SPFA (Bellman-Ford) pass initialises
potentials so negative arc costs are handled (we encode recovery as a NEGATIVE cost to *maximise* it),
then each augmentation uses Dijkstra on non-negative reduced costs — O(E log V) per path, fast enough
for per-bucket optimisation at scale. Integer capacities give integral flows: no float wobble in the
assignment decision.

Drawback-specific semantics: augment along the most-negative-cost source->sink path and STOP as soon
as the cheapest remaining path is non-negative. Because every real import->export arc costs < 0
(recovery > 0) and source/sink arcs cost 0, this yields the flow that MAXIMISES total recovery without
being forced to saturate neutral capacity.

Validated against a brute-force optimum on small inputs in the test suite (D-004 validation plan).
"""

from __future__ import annotations

import heapq
from collections import deque

INF = float("inf")


class MinCostFlow:
    def __init__(self, num_nodes: int) -> None:
        self.n = num_nodes
        # edge = [to, capacity, cost, flow]; residual partner at index ^1
        self.edges: list[list[int]] = []
        self.adj: list[list[int]] = [[] for _ in range(num_nodes)]

    def add_edge(self, u: int, v: int, capacity: int, cost: int) -> int:
        eid = len(self.edges)
        self.adj[u].append(eid)
        self.edges.append([v, capacity, cost, 0])
        self.adj[v].append(eid + 1)
        self.edges.append([u, 0, -cost, 0])
        return eid

    def flow_on(self, eid: int) -> int:
        return self.edges[eid][3]

    def _init_potentials(self, s: int) -> list[float]:
        """Real shortest distances from s via SPFA — valid initial potentials for negative costs."""
        dist = [INF] * self.n
        dist[s] = 0
        in_q = [False] * self.n
        q: deque[int] = deque([s])
        in_q[s] = True
        while q:
            u = q.popleft()
            in_q[u] = False
            du = dist[u]
            for eid in self.adj[u]:
                to, cap, cost, flow = self.edges[eid]
                if cap - flow > 0 and du + cost < dist[to]:
                    dist[to] = du + cost
                    if not in_q[to]:
                        q.append(to)
                        in_q[to] = True
        # Unreachable nodes get potential 0 (they carry no flow until reached).
        return [0 if d is INF else d for d in dist]

    def solve(self, s: int, t: int) -> tuple[int, int]:
        """Push max-recovery flow s->t. Returns (total_flow, total_cost); total_cost <= 0 and
        total recovery = -total_cost (in the engine's integer recovery units)."""
        h = self._init_potentials(s)
        total_flow = 0
        total_cost = 0
        while True:
            dist = [INF] * self.n
            prev_edge = [-1] * self.n
            dist[s] = 0
            pq: list[tuple[float, int]] = [(0, s)]
            while pq:
                d, u = heapq.heappop(pq)
                if d > dist[u]:
                    continue
                for eid in self.adj[u]:
                    to, cap, cost, flow = self.edges[eid]
                    if cap - flow <= 0:
                        continue
                    # reduced cost (>= 0 by the potential invariant)
                    nd = d + cost + h[u] - h[to]
                    if nd < dist[to]:
                        dist[to] = nd
                        prev_edge[to] = eid
                        heapq.heappush(pq, (nd, to))
            if dist[t] is INF:
                break
            real_path_cost = dist[t] + h[t] - h[s]
            if real_path_cost >= 0:
                break  # no strictly-beneficial (negative-cost) augmenting path remains
            # advance potentials
            for v in range(self.n):
                if dist[v] is not INF:
                    h[v] += dist[v]
            # bottleneck along the path
            bottleneck = INF
            v = t
            while v != s:
                eid = prev_edge[v]
                e = self.edges[eid]
                bottleneck = min(bottleneck, e[1] - e[3])
                v = self.edges[eid ^ 1][0]
            bottleneck = int(bottleneck)
            v = t
            while v != s:
                eid = prev_edge[v]
                self.edges[eid][3] += bottleneck
                self.edges[eid ^ 1][3] -= bottleneck
                v = self.edges[eid ^ 1][0]
            total_flow += bottleneck
            total_cost += bottleneck * real_path_cost
        return total_flow, total_cost
