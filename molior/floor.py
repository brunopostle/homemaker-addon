import os
import sys
import ifcopenshell.api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from molior.baseclass import BaseClass
from molior.geometry import matrix_align

run = ifcopenshell.api.run


class Floor(BaseClass):
    """A floor filling a room or space"""

    def __init__(self, args={}):
        super().__init__(args)
        self.below = 0.2
        self.id = ""
        self.ifc = "IFCSLAB"
        self.layerset = [[0.2, "Concrete"], [0.02, "Screed"]]
        self.path = []
        self.type = "molior-floor"
        for arg in args:
            self.__dict__[arg] = args[arg]
        # FIXME implement not_if_stair_below
        self.thickness = 0.0
        for layer in self.layerset:
            self.thickness += layer[0]

    def Ifc(self, ifc):
        """Generate some ifc"""
        entity = run(
            "root.create_entity",
            ifc,
            ifc_class=self.ifc,
            name=self.name,
        )

        element_types = {}
        for element_type in ifc.by_type("IfcSlabType"):
            element_types[element_type.Name] = element_type
        if self.name in element_types:
            myelement_type = element_types[self.name]
        else:
            # we need to create a new IfcSlabType
            myelement_type = ifcopenshell.api.run(
                "root.create_entity",
                ifc,
                ifc_class="IfcSlabType",
                name=self.name,
                predefined_type="FLOOR",
            )
            ifcopenshell.api.run(
                "project.assign_declaration",
                ifc,
                definition=myelement_type,
                relating_context=ifc.by_type("IfcProject")[0],
            )
            ifcopenshell.api.run(
                "material.assign_material",
                ifc,
                product=myelement_type,
                type="IfcMaterialLayerSet",
            )

            mylayerset = ifcopenshell.util.element.get_material(myelement_type)
            for mylayer in self.layerset:
                materials = {}
                for material in ifc.by_type("IfcMaterial"):
                    materials[material.Name] = material
                if mylayer[1] in materials:
                    mymaterial = materials[mylayer[1]]
                else:
                    # we need to create a new material
                    mymaterial = ifcopenshell.api.run(
                        "material.add_material", ifc, name=mylayer[1]
                    )

                layer = ifcopenshell.api.run(
                    "material.add_layer", ifc, layer_set=mylayerset, material=mymaterial
                )
                layer.LayerThickness = mylayer[0]

        run(
            "type.assign_type", ifc, related_object=entity, relating_type=myelement_type
        )

        ifc.assign_storey_byindex(entity, self.level)
        shape = ifc.createIfcShapeRepresentation(
            self.context,
            "Body",
            "SweptSolid",
            [
                ifc.createExtrudedAreaSolid(
                    [self.corner_in(index) for index in range(len(self.path))],
                    self.thickness,
                )
            ],
        )
        run("geometry.assign_representation", ifc, product=entity, representation=shape)
        run(
            "geometry.edit_object_placement",
            ifc,
            product=entity,
            matrix=matrix_align(
                [0.0, 0.0, self.elevation - self.below], [1.0, 0.0, 0.0]
            ),
        )
