Usage
=====

The Homemaker add-on puts two new functions in the Blender *Object* menu:
*Topologise* and *Homemaker*.

To see the add-on in action, select the default Blender scene cube and run
*Object > Homemaker*.  After a couple of seconds, the cube has been replaced by
a Blenderbim IFC project with a single building.  This building is tiny, it
consists of one room two metres wide, with a two metre floor to ceiling height
- this is because the default Blender cube is two metres across.  Note that the
base of the cube has been turned into an IFC Floor, there is an IFC Footing
around the perimeter of the base, the vertical faces have become IFC Walls with
IFC Window openings, etc..  This is a complete IFC model that can be futher
edited in Native IFC software such as Blenderbim, saved as an IFC file and
transferred to other IFC capable software.

Press *Ctrl-Z* to undo, this returns the original cube, scale it a bit to a
more reasonable size for room, ie. scale of 1.5 will make the cube three metres
across and three metres high.  Run Homemaker again and as expected the building
is bigger, this time with taller walls and windows.

What happened?
~~~~~~~~~~~~~~

What is happening here is that the *Topologic* library is used to identify all
the enclosed cells in the mesh, in this case there is only one, everything that
doesn't enclose a cell is discarded, and the resulting geometry is a *Topologic
CellComplex*.  This *CellComplex* is then analysed by Homemaker, generating an
IFC model with building elements defined by the default *style*.  Other
*styles* are available, and these can be created, modified and copied to
produce exactly the building you need.

This *CellComplex* is interesting in its own right, so there is an *Object >
Topologise* function that, instead of creating an IFC model, discovers the
*CellComplex* in the mesh and gives you this as a new mesh.  Runnning
*Topologise* on a cube will just give you a new identical cube, but it becomes
useful for discovering *CellComplexes* inside more complex meshes where faces
overlap but don't connect at vertices.

Designing your building
~~~~~~~~~~~~~~~~~~~~~~~

Homemaker assumes that floors are horizontal and walls are vertical, anything
else is 'roof', 'vault', or 'soffit' depending on if there are rooms below or
above.  A room has a floor and walls all the way around the perimeter, so an
attic room can have sloping ceilings, but they need to meet vertical walls.
Any space that doesn't have a horizontal floor connected to vertical walls will
be assigned a space usage of 'void'.  Floor-to-floor heights can be whatever
you like, and floors don't have to run through the building, so you can have
double height spaces, split-level etc..

By default Homemaker assumes that all rooms are 'living' rooms, so they get
windows and internal connecting doors.  At the moment the behaviour of
room/space types are all hard-coded, but eventually it will be configurable.
There are currently several space types: living, kitchen, circulation, stair,
toilet, bedroom and retail; these primarily control which door and window
configuration gets used: retail on the ground floor can get a series of shop
fronts, no doors are created between kitchens and toilets etc..  Stair elements
are not drawn just yet, this is a future feature.  There are two special space
types: 'outdoor' and 'sahn', these generate outdoor spaces that the 'default'
style constructs with a flat roof supported by perimeter posts.  'Sahn' is an
outdoor space type that is treated as internal circulation - think of a private
courtyard in a riad house.

By default every space in your model has a 'living' type, so you get windows,
doors between rooms, but no external doors.  You can manually assign types by
placing new blender objects (such as a new cube) in each of the spaces: give
the new object the name 'retail' (or 'retail.001' etc..) and the space becomes
a room with this type.  If you forget to name or mis-spell this placeholder you
will get a very small cube-shaped building inside your main building :).
Running the *Topologise* function on a mesh will generate these
widgets/placeholders for you as a floating vertex, just rename them to whatever
room type you need, select everything and run *Homemaker*.

Styles
~~~~~~

The 'default' style is based on measurements of a previous home.

You assign styles by assigning blender materials to faces in the blender
object, the styles are massively configurable and use an inheritance system.
Styles control the size, types and spacing of windows and doors, wall
thickness, psets, decoration, repeating items, nested repeating items (like
railings with intermediate posts).  The styles shipped with the add-on are a
bit limited, they are named: 'default', 'courtyard', 'framing', 'cinema',
'fancy', 'pantsy', 'arcade', 'rustic' and 'tuscan'.

Editing and creating styles is documented in :doc:`user reference <reference>`,
you can probably also figure it out by looking at existing styles in the
``share`` folder.
