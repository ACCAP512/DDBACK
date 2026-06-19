"""Min-cost max-flow primitive: optimality vs brute force, and basic cases (D-004 validation)."""

import random

from drawback.matching.mcmf import MinCostFlow


def _max_recovery(imp_caps, exp_caps, recov):
    n_i, n_e = len(imp_caps), len(exp_caps)
    SRC, SINK = 0, 1 + n_i + n_e
    g = MinCostFlow(SINK + 1)
    for i, c in enumerate(imp_caps):
        g.add_edge(SRC, 1 + i, c, 0)
    for e, c in enumerate(exp_caps):
        g.add_edge(1 + n_i + e, SINK, c, 0)
    for (i, e), r in recov.items():
        if r > 0:
            g.add_edge(1 + i, 1 + n_i + e, min(imp_caps[i], exp_caps[e]), -r)
    _flow, cost = g.solve(SRC, SINK)
    return -cost


def _brute(imp_caps, exp_caps, recov):
    units = [e for e, c in enumerate(exp_caps) for _ in range(c)]
    rem = list(imp_caps)
    best = [0]

    def dfs(k, acc):
        if k == len(units):
            best[0] = max(best[0], acc)
            return
        e = units[k]
        dfs(k + 1, acc)  # leave this export unit unmatched
        for i in range(len(imp_caps)):
            if rem[i] > 0 and recov.get((i, e), 0) > 0:
                rem[i] -= 1
                dfs(k + 1, acc + recov[(i, e)])
                rem[i] += 1

    dfs(0, 0)
    return best[0]


def test_basic_lesser_of_pairing():
    # imports D=[10,1], exports E=[10,1] -> optimal pairs (10,10)+(1,1) = 11
    assert _max_recovery([1, 1], [1, 1], {(0, 0): 10, (0, 1): 1, (1, 0): 1, (1, 1): 1}) == 11


def test_mcmf_matches_brute_force_random():
    rng = random.Random(12345)
    for _ in range(300):
        n_i, n_e = rng.randint(1, 3), rng.randint(1, 3)
        imp_caps = [rng.randint(1, 3) for _ in range(n_i)]
        exp_caps = [rng.randint(1, 2) for _ in range(n_e)]
        recov = {(i, e): rng.randint(0, 9) for i in range(n_i) for e in range(n_e) if rng.random() < 0.8}
        assert _max_recovery(imp_caps, exp_caps, recov) == _brute(imp_caps, exp_caps, recov)
