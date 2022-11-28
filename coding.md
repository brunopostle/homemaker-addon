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
                - `IfcSpace`
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

## Context

The *Geometric Representation Context* can only have one of three *ContextType* values, here shown with some common *ContextIdentifier* and *TargetView* values for sub-contexts:

- *Model*
  - *Box* (`MODEL_VIEW`)
  - *Axis* (`GRAPH_VIEW`)
  - *Surface*
  - *Reference* (`GRAPH_VIEW`)
  - *Body* (`MODEL_VIEW`)
- *Plan*
  - *Annotation* (`PLAN_VIEW`)
  - *Axis* (`PLAN_VIEW`)
  - *FootPrint* (`PLAN_VIEW`)
- *NotDefined*

The *Geometric Representation SubContext* has a *ContextIdentifier* (confusingly called the *RepresentationIdentifier* in a *Shape Representation*) that can only have one of eleven values:

- *CoG* (Point to identify the center of gravity of an element. This value can be used for validation purposes)
- *Box* (Bounding box as simplified 3D box geometry of an element)
- *Annotation* (2D annotations not representing elements)
- *Axis* (2D or 3D Axis, or single line, representation of an element)
- *FootPrint* (2D Foot print, or double line, representation of an element, projected to ground view)
- *Profile* (3D line representation of a profile being planar, e.g. used for door and window outlines)
- *Surface* (3D Surface representation, e.g. of an analytical surface, of an elementplane)
- *Reference* (3D representation that is not part of the Body representation. This is used, e.g., for opening geometries, if there are to be excluded from an implicit Boolean operation)
- *Body* (3D Body representation, e.g. as wireframe, surface, or solid model, of an element)
- *Clearance* (3D clearance volume of the element. Such clearance region indicates space that should not intersect with the 'Body' representation of other elements, though may intersect with the 'Clearance' representation of other elements)
- *Lighting* (Representation of emitting light as a light source within a shape representation)

The *TargetView* has one of nine *Geometric Projection Enum* values:

- `GRAPH_VIEW`
- `SKETCH_VIEW`
- `MODEL_VIEW`
- `PLAN_VIEW`
- `REFLECTED_PLAN_VIEW`
- `SECTION_VIEW`
- `ELEVATION_VIEW`
- `USERDEFINED`
- `NOTDEFINED`

A *Shape Representation* can have one of these *RepresentationType* values:

- *Point* (2 or 3 dimensional point(s))
- *PointCloud* (3 dimensional points represented by a point list)
- *Curve* (2 or 3 dimensional curve(s))
- *Curve2D* (2 dimensional curve(s))
- *Curve3D* (3 dimensional curve(s))
- *Surface* (2 or 3 dimensional surface(s))
- *Surface2D* (2 dimensional surface(s) (a region on ground view))
- *Surface3D* (3 dimensional surface(s))
- *FillArea* (2D region(s) represented as a filled area (hatching))
- *Text* (text defined as text literals)
- *AdvancedSurface* (3 dimensional b-spline surface(s))
- *GeometricSet* (points, curves, surfaces (2 or 3 dimensional))
  - *GeometricCurveSet* (points, curves (2 or 3 dimensional))
  - *Annotation2D* (points, curves (2 or 3 dimensional), hatches and text (2 dimensional))
- *SurfaceModel* (face based and shell based surface model(s), or tessellated surface model(s))
  - *Tessellation* (tessellated surface representation(s) only)
- *SolidModel* (including swept solid, Boolean results and Brep bodies; more specific types are:)
  - *SweptSolid* (swept area solids, by extrusion and revolution, excluding tapered sweeps)
  - *AdvancedSweptSolid* (swept area solids created by sweeping a profile along a directrix, and tapered sweeps)
  - *Brep* (faceted Brep's with and without voids)
  - *AdvancedBrep* (Brep's based on advanced faces, with b-spline surface geometry, with and without voids)
  - *CSG* (Boolean results of operations between solid models, half spaces and Boolean results)
  - *Clipping* (Boolean differences between swept area solids, half spaces and Boolean results)
- *BoundingBox* (simplistic 3D representation by a bounding box)
- *SectionedSpine* (cross section based representation of a spine curve and planar cross sections. It can represent a surface or a solid and the interpolations of the between the cross sections is not defined)
- *LightSource* (light source with (depending on type) position, orientation, light colour, intensity and attenuation)
- *MappedRepresentation* (representation based on mapped item(s), referring to a representation map. Note: it can be seen as an inserted block reference. The shape representation of the mapped item has a representation type declaring the type of its representation items.)
