# 'plate' style

Every face becomes a flat IfcPlate, centred on the face, with a matching
structural surface member. There are no windows, doors, footings or other
details. This is for sculptural meshes that are to be analysed, typically in
'lite mode' as they don't enclose rooms: see `Molior.from_topology()`.

Plates are 10mm steel. To use something else, change the IfcMaterialLayer and
material in `library.ifc`, or make a sub-style with its own. `hulls.yml` needs to
agree: `structural_thickness` and `structural_material` for the analysis model,
and `offset`, which is minus half the thickness to centre plates on the face.

Connected faces need to have normals that all point the same way.
