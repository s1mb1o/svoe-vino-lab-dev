import numpy as np

from shelfreid.homography import project
from shelfreid.posegraph import PoseGraph

SIZE = (540, 960)


def shift(dx, dy=0.0):
    return np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]], float)


def test_a_loop_closure_spreads_the_drift_over_the_path():
    # A camera pans right in 10 steps of 200 px and comes back to the start. Each
    # odometry step overstates the move by 6 px, so the chain ends 60 px off.
    truth = [shift(200.0 * k) for k in range(11)]
    graph = PoseGraph(SIZE)
    graph.add(np.eye(3))
    for k in range(1, 11):
        measured = shift(206.0)                       # keyframe k -> keyframe k-1
        node = graph.add(graph.poses[-1] @ measured)
        graph.connect(node - 1, node, measured)
    # The loop: the last keyframe registered directly to keyframe 5 (exact).
    graph.connect(5, 10, np.linalg.inv(truth[5]) @ truth[10], weight=2.0, kind="loop")
    loop = graph.edges[-1]
    assert graph.error(loop) > 25
    before, after = graph.optimize()
    assert graph.error(loop) < 6
    # The graph holds relative measurements only: the first five steps keep their 6 px
    # each (node 5 is 30 px off), and the 30 px of the loop spread over nodes 5-10, so the
    # last node ends about 33 px off. The nodes MUST keep their scale and perspective.
    grid = graph.grid
    worst = max(np.linalg.norm(project(G, grid) - project(T, grid), axis=1).max()
                for G, T in zip(graph.poses, truth))
    assert worst < 45
    assert all(abs(G[0, 0] - 1) < 0.015 and abs(G[1, 1] - 1) < 0.015 for G in graph.poses)
    assert after < before


def test_the_first_pose_stays_fixed():
    graph = PoseGraph(SIZE)
    graph.add(np.eye(3))
    node = graph.add(shift(100.0))
    graph.connect(0, node, shift(90.0))
    graph.optimize()
    assert np.allclose(graph.poses[0], np.eye(3))
    assert abs(graph.poses[1][0, 2] - 90.0) < 1.0


def test_a_bad_loop_is_dropped_beside_another_edge_of_its_pair():
    # Two edges of one pair (a chain and a loop) and a false loop far off: the robust
    # optimisation drops the false one by identity, not by comparing the edge fields.
    graph = PoseGraph(SIZE)
    graph.add(np.eye(3))
    node = graph.add(shift(100.0))
    graph.connect(0, node, shift(100.0))
    graph.connect(0, node, shift(101.0), weight=0.5, kind="chain")
    graph.connect(0, node, shift(900.0), weight=2.0, kind="loop")
    _, _, dropped = graph.optimize_robust()
    assert dropped == 1
    assert all(e.kind != "loop" for e in graph.edges)
    assert abs(graph.poses[1][0, 2] - 100.0) < 2.0
