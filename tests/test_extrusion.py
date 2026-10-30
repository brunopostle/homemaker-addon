#!/usr/bin/python3

import os
import sys
import pytest
from topologic_core import Vertex

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import topologist.ugraph as ugraph
import topologist.normals
import ifcopenshell.geom
import numpy
from molior import Molior
from molior.rooms import document_to_faces_and_widgets
from molior.style import Style
import molior.ifc


@pytest.fixture
def closed_extrusion():
    trace = ugraph.graph()
    normals = topologist.normals.Normals()
    vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
    vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
    vertex_2 = Vertex.ByCoordinates(8.0, 4.0, 3.15)
    vertex_3 = Vertex.ByCoordinates(1.0, 4.0, 3.15)
    coor_0 = vertex_0.CoorAsString()
    coor_1 = vertex_1.CoorAsString()
    coor_2 = vertex_2.CoorAsString()
    coor_3 = vertex_3.CoorAsString()

    # closed extrusion
    # string: [string, [Vertex, Vertex, Face, Cell, Cell]]
    trace.add_edge(
        {
            coor_1: [
                coor_2,
                {
                    "start_vertex": vertex_1,
                    "end_vertex": vertex_2,
                    "face": None,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            coor_0: [
                coor_1,
                {
                    "start_vertex": vertex_0,
                    "end_vertex": vertex_1,
                    "face": None,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            coor_2: [
                coor_3,
                {
                    "start_vertex": vertex_2,
                    "end_vertex": vertex_3,
                    "face": None,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            coor_3: [
                coor_0,
                {
                    "start_vertex": vertex_3,
                    "end_vertex": vertex_0,
                    "face": None,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    paths = trace.find_paths()

    ifc = molior.ifc.init(name="Our Project")

    molior_object = Molior(
        file=ifc,
        circulation=None,
        normals=normals.normals,
        name="My House",
        elevations={3.15: 2},
    )
    molior_object.init_building()
    extrusion = molior_object.build_trace(
        stylename="default",
        condition="top-backward-up",
        elevation=3.15,
        height=0.05,
        chain=paths[0],
    )

    return extrusion


@pytest.fixture
def open_extrusion():
    trace = ugraph.graph()
    normals = topologist.normals.Normals()
    vertex_0 = Vertex.ByCoordinates(1.0, 0.0, 3.15)
    vertex_1 = Vertex.ByCoordinates(5.0, 0.0, 3.15)
    vertex_2 = Vertex.ByCoordinates(8.0, 4.0, 3.15)
    vertex_3 = Vertex.ByCoordinates(1.0, 4.0, 3.15)
    coor_0 = vertex_0.CoorAsString()
    coor_1 = vertex_1.CoorAsString()
    coor_2 = vertex_2.CoorAsString()
    coor_3 = vertex_3.CoorAsString()

    # open extrusion
    trace = ugraph.graph()
    trace.add_edge(
        {
            coor_1: [
                coor_2,
                {
                    "start_vertex": vertex_1,
                    "end_vertex": vertex_2,
                    "face": None,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            coor_0: [
                coor_1,
                {
                    "start_vertex": vertex_0,
                    "end_vertex": vertex_1,
                    "face": None,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    trace.add_edge(
        {
            coor_2: [
                coor_3,
                {
                    "start_vertex": vertex_2,
                    "end_vertex": vertex_3,
                    "face": None,
                    "back_cell": None,
                    "front_cell": None,
                },
            ]
        }
    )
    paths = trace.find_paths()

    ifc = molior.ifc.init(name="Our Project")

    molior_object = Molior(
        file=ifc,
        circulation=None,
        normals=normals.normals,
        name="My House",
        elevations={3.15: 2},
    )
    molior_object.init_building()
    extrusion = molior_object.build_trace(
        stylename="default",
        condition="top-backward-level",
        elevation=3.15,
        height=0.05,
        chain=paths[0],
    )
    ifc.write("_test.ifc")

    return extrusion


def test_closed_extrusion_properties(closed_extrusion):
    assert len(closed_extrusion) == 3
    assert closed_extrusion[0].level == 2
    assert closed_extrusion[0].name == "eaves corona"
    assert closed_extrusion[0].typename == "eaves_corona"
    assert closed_extrusion[0].__dict__["class"] == "Extrusion"


if __name__ == "__main__":
    pytest.main()


def _one_room(stylename):
    faces, widgets = document_to_faces_and_widgets(
        {
            "rooms": [
                {
                    "vertices": [[0, 0], [6, 0], [6, 6], [0, 6]],
                    "elevation": 0.0,
                    "height": 3.43,
                    "stylename": stylename,
                    "usage": "living",
                }
            ]
        }
    )
    return Molior.from_faces_and_widgets(faces=faces, widgets=widgets)


def test_rustic_crown_is_on_the_wall_face():
    molior_object = _one_room("rustic")
    molior_object.execute()

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    def min_x(element):
        shape = ifcopenshell.geom.create_shape(settings, element)
        return numpy.array(shape.geometry.verts).reshape(-1, 3)[:, 0].min()

    crowns = [
        item
        for item in molior_object.file.by_type("IfcCovering")
        if item.Name == "crown"
    ]
    walls = molior_object.file.by_type("IfcWall")
    assert crowns
    wall_face = min(min_x(wall) for wall in walls)
    assert min(min_x(crown) for crown in crowns) == pytest.approx(
        wall_face - 0.0887, abs=0.001
    )


def test_type_without_profile_is_reported(monkeypatch):
    get_from_library = Style.get_from_library

    def no_crown(self, stylename, ifc_class, name):
        if name == "crown":
            return (None, None, None)
        return get_from_library(self, stylename, ifc_class, name)

    monkeypatch.setattr(Style, "get_from_library", no_crown)
    molior_object = _one_room("default")
    with pytest.raises(ValueError, match="IfcCoveringType 'crown'"):
        molior_object.execute()
