# Naming conventions

## Entity

Any IFC class instance, a line in an IFC file.

## Instance

There may be multiple entity instances of a particular IFC class.

## Object

Any `IfcObject` sub-class. A thing, process, person or concept.

All *Object* entities are derived from `IfcRoot`, so they have
*GlobalId*, *OwnerHistory*, *Name*, and *Description* attributes.

May be used in *Relationship* entities, for *RelatingObject* and
*RelatedObjects* e.g in aggregation (beware that `object` is a python
reserved word).

Create rooted Object entities using the `root.create_entity` API, this looks
after all the *GlobalId* and *OwnerHistory* stuff.

## Product

Any `IfcProduct` sub-class. Includes *Element* entities (such as
`IfcWall`), *Structural Item* entities (such as
`IfcStructuralCurveMember`), and *Spatial Element* entities (such as
`IfcBuilding`).

All *Product* entities are by inheritance *Object* entities.

A *Product* also has *ObjectPlacement* and *Representation* attributes.

## Element

Any `IfcElement` sub-class, all *Element* entities are by inheritance
*Object* and *Product* entities. *Element* entities are physically
existing things such a `IfcWall` that have a *Shape Representation*.
Distinct from a *Spatial Element* such as a `IfcBuilding`.

## Item

Typically a *Representation Item*, such as a *Styled Item* or *Geometric
Representation Item* (such as a *Placement*, *Point* or *Solid Model*).

*Representation Item* entities are not derived from `IfcRoot`, so they
don't have *GlobalId* or *OwnerHistory* attributes. There are other
entities that are also named *Item*, such as *Structural Item* that
actually are derived from `IfcRoot`, go figure.

## Some typical entities and where they fit in

- Root
    - Object
        - Product
            - Spatial Element
                - `IfcBuilding`
                - `IfcBuildingStorey`
                - `IfcSite`
            - Element
                - `IfcBeam`
                - `IfcBuildingElementProxy`
                - `IfcColumn`
                - `IfcDoor`
                - `IfcFooting`
                - `IfcOpeningElement`
                - `IfcRailing`
                - `IfcRoof`
                - `IfcWall`
                - `IfcWindow`
            - Structural Item
                - `IfcStructuralCurveConnection`
                - `IfcStructuralCurveMember`
                - `IfcStructuralPointConnection`
                - `IfcStructuralSurfaceMember`
    - `IfcProject`
    - `IfcProjectLibrary`
    - Relationship
        - `IfcRelAssignsToProduct`
        - `IfcRelSpaceBoundary2ndLevel`
- Representation
    - `IfcShapeRepresentation`
    - `IfcTopologyRepresentation`
- Representation Item
    - Geometric Representation Item
        - `IfcAxis2Placement3D`
        - `IfcBooleanClippingResult`
        - `IfcBooleanResult`
        - `IfcCartesianPoint`
        - `IfcCartesianPointList3D`
        - `IfcCartesianTransformationOperator2D`
        - `IfcCurveBoundedPlane`
        - `IfcDirection`
        - `IfcExtrudedAreaSolid`
        - `IfcIndexedPolygonalFace`
        - `IfcPlane`
        - `IfcPolygonalBoundedHalfSpace`
        - `IfcPolygonalFaceSet`
        - `IfcPolyline`
        - `IfcSurfaceCurveSweptAreaSolid`
    - Topological Representation Item
        - `IfcEdge`
        - `IfcEdgeLoop`
        - `IfcFaceBound`
        - `IfcFaceSurface`
        - `IfcOrientedEdge`
        - `IfcVertexPoint`
- Connection Geometry
    - `IfcConnectionSurfaceGeometry`
- Profile Def
    - `IfcArbitraryClosedProfileDef`
    - `IfcDerivedProfileDef`
- Material Definition
    - `IfcMaterialProfile`
    - `IfcMaterialProfileSet`
