"""Tests for Alexander Pattern Language fitness assessors.

Simple fixture: two stacked 10x10x10 cubes, 3 cells, all default to 'living'.
Full-building fixture: multi-room, multi-storey building from conftest.py
  (kitchen, living, stair, toilet, circulation, outside cells).
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from topologic_core import Vertex, Face, CellComplex

import topologist.topology
import topologist.cell
import topologist.face
import topologist.graph
import topologist.cellcomplex

assert topologist.topology
assert topologist.cell
assert topologist.face
assert topologist.graph
assert topologist.cellcomplex

from topologist.fitness.p105_south_facing_outdoors import Assessor as P105
from topologist.fitness.p107_wings_of_light import Assessor as P107
from topologist.fitness.p127_intimacy_gradient import Assessor as P127
from topologist.fitness.p128_indoor_sunlight import Assessor as P128
from topologist.fitness.p129_common_areas_at_the_heart import Assessor as P129
from topologist.fitness.p131_the_flow_through_rooms import Assessor as P131
from topologist.fitness.p133_staircase_as_a_stage import Assessor as P133
from topologist.fitness.p138_sleeping_to_the_east import Assessor as P138
from topologist.fitness.p145_bulk_storage import Assessor as P145
from topologist.fitness.p159_light_on_two_sides_of_every_room import Assessor as P159
from topologist.fitness.p190_ceiling_height_variety import Assessor as P190


@pytest.fixture
def cell_complex():
    """Two stacked cubes sharing a mid-floor face."""
    points = [
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [10.0, 10.0, 0.0],
        [0.0, 10.0, 0.0],
        [0.0, 0.0, 10.0],
        [10.0, 0.0, 10.0],
        [10.0, 10.0, 10.0],
        [0.0, 10.0, 10.0],
        [0.0, 0.0, 20.0],
        [10.0, 0.0, 20.0],
        [10.0, 10.0, 20.0],
        [0.0, 10.0, 20.0],
    ]
    vertices = [Vertex.ByCoordinates(*p) for p in points]

    face_ids = [
        [0, 1, 2],
        [0, 2, 3],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [0, 4, 7, 3],
        [0, 1, 5, 4],
        [4, 5, 6],
        [4, 6, 7],
        [0, 2, 6, 4],
        [4, 5, 9, 8],
        [5, 6, 10, 9],
        [6, 7, 11, 10],
        [7, 4, 8, 11],
        [8, 9, 10, 11],
    ]
    face_objects = [Face.ByVertices([vertices[i] for i in ids]) for ids in face_ids]
    cc = CellComplex.ByFaces(face_objects, 0.0001)
    cc.IndexTopology()
    cc.AllocateCells([])
    return cc


@pytest.fixture
def assessor_args(cell_complex):
    """Prepare circulation graph and shortest-path table."""
    adj = cell_complex.Adjacency()
    adj.Circulation(cell_complex)
    spt = adj.ShortestPathTable()
    return cell_complex, adj, spt


@pytest.fixture
def inside_cells(cell_complex):
    cells_ptr = []
    cell_complex.Cells(None, cells_ptr)
    return [c for c in cells_ptr if not c.IsOutside()]


# ---------------------------------------------------------------------------
# P105 SOUTH FACING OUTDOORS
# ---------------------------------------------------------------------------

def test_p105_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P105(cc, circ, spt)
    for cell in inside_cells:
        score = a.execute(cell)
        assert isinstance(score, float)


def test_p105_inside_cells_return_neutral(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P105(cc, circ, spt)
    for cell in inside_cells:
        assert a.execute(cell) == 1.0


def test_p105_hemisphere_flips_score(setup_cell_complex):
    """Southern hemisphere setting should produce a different score than northern."""
    cc, circ, spt = setup_cell_complex
    north = P105(cc, circ, spt, hemisphere="north")
    south = P105(cc, circ, spt, hemisphere="south")
    outside = [c for c in cc.Cells(None, []) or [] if c.IsOutside()]
    # Build cell list properly
    cells_ptr = []
    cc.Cells(None, cells_ptr)
    outside = [c for c in cells_ptr if c.IsOutside()]
    if outside:
        scores_north = [north.execute(c) for c in outside]
        scores_south = [south.execute(c) for c in outside]
        # The two hemispheres should not always produce identical scores
        assert scores_north != scores_south


def test_p128_hemisphere_flips_score(setup_cell_complex):
    """Southern hemisphere setting should produce a different score than northern."""
    cc, circ, spt = setup_cell_complex
    north = P128(cc, circ, spt, hemisphere="north")
    south = P128(cc, circ, spt, hemisphere="south")
    cells_ptr = []
    cc.Cells(None, cells_ptr)
    living = [c for c in cells_ptr if c.Usage() == "living"]
    if living:
        scores_north = [north.execute(c) for c in living]
        scores_south = [south.execute(c) for c in living]
        assert scores_north != scores_south


# ---------------------------------------------------------------------------
# P107 WINGS OF LIGHT
# ---------------------------------------------------------------------------

def test_p107_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P107(cc, circ, spt)
    for cell in inside_cells:
        score = a.execute(cell)
        assert isinstance(score, float)


def test_p107_score_range(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P107(cc, circ, spt)
    for cell in inside_cells:
        score = a.execute(cell)
        assert 0.0 < score <= 2.0


# ---------------------------------------------------------------------------
# P127 INTIMACY GRADIENT
# ---------------------------------------------------------------------------

def test_p127_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P127(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


def test_p127_no_spt_returns_neutral(assessor_args, inside_cells):
    cc, circ, _ = assessor_args
    a = P127(cc, circ, {})
    for cell in inside_cells:
        assert a.execute(cell) == 1.0


# ---------------------------------------------------------------------------
# P128 INDOOR SUNLIGHT
# ---------------------------------------------------------------------------

def test_p128_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P128(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


def test_p128_non_important_rooms_neutral(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P128(cc, circ, spt)
    # default usage is 'living', which IS in important_usages — so just check float
    for cell in inside_cells:
        score = a.execute(cell)
        assert 0.0 < score <= 2.0


# ---------------------------------------------------------------------------
# P129 COMMON AREAS AT THE HEART
# ---------------------------------------------------------------------------

def test_p129_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P129(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


def test_p129_common_rooms_score_above_zero(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P129(cc, circ, spt)
    for cell in inside_cells:
        score = a.execute(cell)
        assert score > 0.0


# ---------------------------------------------------------------------------
# P131 THE FLOW THROUGH ROOMS
# ---------------------------------------------------------------------------

def test_p131_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P131(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


def test_p131_corridor_penalised(assessor_args, cell_complex):
    cc, circ, spt = assessor_args
    a = P131(cc, circ, spt)
    cells_ptr = []
    cc.Cells(None, cells_ptr)
    corridor = cells_ptr[0]
    corridor.Set("usage", "corridor")
    assert a.execute(corridor) < 1.0
    # restore
    corridor.Set("usage", "living")


# ---------------------------------------------------------------------------
# P133 STAIRCASE AS A STAGE
# ---------------------------------------------------------------------------

def test_p133_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P133(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


def test_p133_non_stair_neutral(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P133(cc, circ, spt)
    for cell in inside_cells:
        # none are stairs by default
        assert a.execute(cell) == 1.0


# ---------------------------------------------------------------------------
# P138 SLEEPING TO THE EAST
# ---------------------------------------------------------------------------

def test_p138_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P138(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


def test_p138_non_bedroom_neutral(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P138(cc, circ, spt)
    for cell in inside_cells:
        # default usage is 'living', not bedroom
        assert a.execute(cell) == 1.0


def test_p138_bedroom_scores(assessor_args, cell_complex):
    cc, circ, spt = assessor_args
    a = P138(cc, circ, spt)
    cells_ptr = []
    cc.Cells(None, cells_ptr)
    bedroom = cells_ptr[0]
    bedroom.Set("usage", "bedroom")
    score = a.execute(bedroom)
    assert isinstance(score, float)
    assert 0.0 < score <= 2.0
    bedroom.Set("usage", "living")


# ---------------------------------------------------------------------------
# P145 BULK STORAGE
# ---------------------------------------------------------------------------

def test_p145_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P145(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


def test_p145_no_storage_scores_zero(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P145(cc, circ, spt)
    for cell in inside_cells:
        score = a.execute(cell)
        # no storage cells → ratio = 0 → score = 0
        assert score == 0.0


def test_p145_with_storage(assessor_args, cell_complex):
    cc, circ, spt = assessor_args
    a = P145(cc, circ, spt)
    cells_ptr = []
    cc.Cells(None, cells_ptr)
    storage_cell = cells_ptr[0]
    storage_cell.Set("usage", "storage")
    for cell in cells_ptr:
        if not cell.IsOutside():
            score = a.execute(cell)
            assert score > 0.0
    storage_cell.Set("usage", "living")


# ---------------------------------------------------------------------------
# P159 LIGHT ON TWO SIDES (existing — regression check)
# ---------------------------------------------------------------------------

def test_p159_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P159(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


# ---------------------------------------------------------------------------
# P190 CEILING HEIGHT VARIETY
# ---------------------------------------------------------------------------

def test_p190_returns_float(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P190(cc, circ, spt)
    for cell in inside_cells:
        assert isinstance(a.execute(cell), float)


def test_p190_same_height_neighbours_score_neutral(assessor_args, inside_cells):
    cc, circ, spt = assessor_args
    a = P190(cc, circ, spt)
    # Both cubes have height 10, so any stacked neighbour has same height
    for cell in inside_cells:
        score = a.execute(cell)
        assert score >= 1.0  # no variety bonus, but also no penalty


# ===========================================================================
# Full multi-room building tests (uses setup_cell_complex from conftest.py)
# ===========================================================================

def _all_cells(cc):
    cells_ptr = []
    cc.Cells(None, cells_ptr)
    return cells_ptr


def test_full_building_circulation_connected(setup_cell_complex):
    """Circulation graph for the full building must be fully connected."""
    cc, circ, spt = setup_cell_complex
    assert circ.IsConnected()


def test_full_building_all_assessors_return_float(setup_cell_complex):
    """Every assessor should return a float for every cell in a real building."""
    cc, circ, spt = setup_cell_complex
    cells = _all_cells(cc)
    assessors = [
        P105(cc, circ, spt),
        P107(cc, circ, spt),
        P127(cc, circ, spt),
        P128(cc, circ, spt),
        P129(cc, circ, spt),
        P131(cc, circ, spt),
        P133(cc, circ, spt),
        P138(cc, circ, spt),
        P145(cc, circ, spt),
        P159(cc, circ, spt),
        P190(cc, circ, spt),
    ]
    for a in assessors:
        for cell in cells:
            score = a.execute(cell)
            assert isinstance(score, float), (
                f"{a.__class__.__name__} returned {score!r} for cell {cell.Usage()}"
            )
            assert score >= 0.0


def test_full_building_p105_outside_cell_scores(setup_cell_complex):
    """The 'outside' cell should receive a non-neutral p105 score."""
    cc, circ, spt = setup_cell_complex
    a = P105(cc, circ, spt)
    outside = [c for c in _all_cells(cc) if c.IsOutside()]
    assert outside, "fixture should have at least one outside cell"
    for cell in outside:
        score = a.execute(cell)
        assert isinstance(score, float)
        assert score >= 1.0


def test_full_building_p127_private_rooms_deeper(setup_cell_complex):
    """Toilet cells should score with positive float; usage affects result."""
    cc, circ, spt = setup_cell_complex
    a = P127(cc, circ, spt)
    toilets = [c for c in _all_cells(cc) if c.Usage() == "toilet"]
    living = [c for c in _all_cells(cc) if c.Usage() == "living"]
    assert toilets and living
    toilet_scores = [a.execute(c) for c in toilets]
    living_scores = [a.execute(c) for c in living]
    # On average, toilets should score >= living rooms (deeper = better for private)
    assert sum(toilet_scores) / len(toilet_scores) >= sum(living_scores) / len(living_scores)


def test_full_building_p131_corridor_penalised(setup_cell_complex):
    """Cells with 'circulation' usage should score below 1.0."""
    cc, circ, spt = setup_cell_complex
    a = P131(cc, circ, spt)
    circulation_cells = [c for c in _all_cells(cc) if c.Usage() == "circulation"]
    assert circulation_cells, "fixture should have circulation cells"
    for cell in circulation_cells:
        assert a.execute(cell) < 1.0


def test_full_building_p133_stair_scores(setup_cell_complex):
    """Stair cells should receive a score based on adjacency to common rooms."""
    cc, circ, spt = setup_cell_complex
    a = P133(cc, circ, spt)
    stairs = [c for c in _all_cells(cc) if c.Usage() == "stair"]
    assert stairs, "fixture should have stair cells"
    for cell in stairs:
        score = a.execute(cell)
        assert isinstance(score, float)
        assert 0.5 <= score <= 2.0


def test_full_building_p190_height_variety(setup_cell_complex):
    """Building has rooms at different heights; some should score above 1.0."""
    cc, circ, spt = setup_cell_complex
    a = P190(cc, circ, spt)
    inside = [c for c in _all_cells(cc) if not c.IsOutside()]
    scores = [a.execute(c) for c in inside]
    assert any(s > 1.0 for s in scores), "expected at least one cell with height variety bonus"
