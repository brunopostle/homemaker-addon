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

- Adaptable style system, styles can be subclassed or overrriden entirely.
Different parts of buildings can be assigned different styles.

- Fully compliant industry standard IFC output.

- Free Software, no annual licenses, these are your tools to use, customise and
share as you wish.

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
be done: repeating and nested elements, subtractive geometry etc.

- Assets such as windows, doors and extrusion profiles are currently provided
in DXF format, we need a really good system for creating and editing these
as native IFC objects.

- Materials have been lost in the process of porting from Perl, we need to be
able to control what our buildings are made-from.

- Costing. IFC can hold detailed information on quantities, costs and
scheduling, the library needs to make this stuff easy.

- Structural and environmental analysis. The high-level models used in this
library are well-suited for providing input to structural and thermal
analysis software.

- But not least, let's take architecture out of the hands of architects and put
it back in the hands of people who need good ordinary buildings.

## Requirements

- [topologicPy](https://github.com/wassimj/topologicPy) a python interface to the TopologicCore library. Install it with `sudo python setup.py install`
  - [cppyy](https://pypi.org/project/cppyy/) C++ python interface, this consists of four packages: `cppyy-cling`, `cppyy_backend`, `CPyCppyy` and `cppyy`, but you can probably install it all with `sudo pip install cppyy`
  - [TopologicCore](https://github.com/NonManifoldTopology/Topologic). This is a C++ library which you build and install using the standard cmake build system. It requires the opencascade library and headers which should be available from your distribution.
- [blenderbim](https://blenderbim.org/) blender add-on, just download the ZIP and install from the blender preferences menu.
- [pyyaml](https://pyyaml.org/) python module.
- [ezdxf](https://ezdxf.readthedocs.io/en/stable/index.html) python module for reading assets, which are in DXF format until we can figure out how to use IFC asset libraries.

## About

This software would not be possible without leaning heavily on other software,
in particular Topologic, Blenderbim and IfcOpenShell.

The homemaker-addon is a python port of the Homemaker [Topologise blender add-on](https://bitbucket.org/brunopostle/urb/src/master/blender/topologise.py).

Copyright 2021, Bruno Postle <bruno@postle.net>
License: GPLv3
