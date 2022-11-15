# Homemaker add-on

*Design buildings the pointy-clicky way*

## About

The [Homemaker add-on](https://github.com/brunopostle/homemaker-addon) tries to
automate the tedious work of designing buildings.  Just indicate with simple
geometry where you want walls, floors and roofs, and the software figures-out
what building elements are needed to create that building. The result is an
industry-standard IFC (BIM) model, suitable for taking the project towards
construction.

The software is a general python library for turning 3D geometry and style
definitions into IFC building models, it is initially provided as a Blender
add-on, but is designed to be usable with other awesome 3D design platforms
such as FreeCAD.

## Features

- Will assemble buildings from any geometry, as long as the faces overlap
enough to define cells for rooms.  The only assumption is that walls are
vertical and floors are horizontal.

- Adaptable style system, styles can be subclassed or overridden entirely.
Different parts of buildings can be assigned different styles.

- Fully compliant industry standard IFC output.

- Free Software, no annual licenses, these are your tools to use, customise and
share as you wish.

## Documentation

There is some [Homemaker reference and API
documentation](https://homemaker-addon.readthedocs.io)

## Roadmap

This is a big project that will take a lot of work to reach its full potential,
so the following are just a few of the areas where help is welcome:

- Pattern Languages. The main [Homemaker evolutionary design tool](https://bitbucket.org/brunopostle/urb/wiki/Home), illustrates that Pattern Languages form a complete theory of architecture.
By adding an evolution engine with a Pattern Language as fitness criteria it
shows it is possible to design humane buildings that are a good fit to their
environment, fully automatically.  This add-on builds-on this result but
creates the interactive design tool that is needed.  The high-level models
created in this library are well suited for assessment using a Pattern
Language, so a priority is to implement as many patterns as possible to guide
the hand of the designer with continuous and early feedback.

- Management of circulation and stairs was lost when porting from Perl, this
needs reimplementing.

- Other platforms in addition to Blender, i.e. FreeCAD

- Extended style system, buildings can be styled with an extensive inheritable
style system, but this is just the start, there is lots more that needs to
be done: grillages, subtractive geometry etc.

- Assets such as windows, doors and extrusion profiles are currently provided
in DXF format, these need to be ported to a native IFC Library.

- Costing, Carbon and Life Cycle Analysis. IFC can hold detailed information on
quantities, costs and scheduling, the library needs to make this stuff easy.

- Structural and environmental analysis. The generated models contain IFC
Structural Model data and 2nd Level Space Boundary data for thermal analysis,
these need testing in a range of analysis software.

- But not least, let's take architecture out of the hands of architects and put
it back in the hands of people who need good ordinary buildings.

## Requirements

- [topologic](https://github.com/wassimj/Topologic) a pybind11 python interface to the TopologicCore library.
  - [TopologicCore](https://github.com/wassimj/Topologic). This is a C++ library which you build and install using the standard cmake build system. It requires the opencascade library and headers which should be available from your distribution.
- [blenderbim](https://blenderbim.org/) blender add-on, just download the ZIP and install from the blender preferences menu.
- [pyyaml](https://pyyaml.org/) python module.

## About

This software would not be possible without leaning heavily on other software,
in particular Topologic, Blenderbim and IfcOpenShell.

The homemaker-addon is a python port of the Homemaker [Topologise blender add-on](https://bitbucket.org/brunopostle/urb/src/master/blender/topologise.py).

Copyright 2021, Bruno Postle <bruno@postle.net>
License: GPLv3.
3D and 2D asset and style files bundled with this software are additionally licensed 'CC BY 4.0'
