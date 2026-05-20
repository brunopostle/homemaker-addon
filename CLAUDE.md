# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Homemaker is a Blender add-on for automating building design. It converts simple 3D geometry (faces representing walls, floors, roofs) into industry-standard IFC (Building Information Modeling) files. The software uses Topologic for 3D geometry processing and IfcOpenShell for IFC model generation.

**Key concept**: Users draw simple overlapping faces in Blender to define building volumes. Homemaker analyzes this geometry to identify rooms (cells) and building elements, then generates a complete IFC building model.

## Development Commands

### Testing
```bash
# Run all tests
make test
# or
pytest tests/

# Run a single test file
pytest tests/test_wall.py

# Run a specific test
pytest tests/test_wall.py::test_function_name

# Run with coverage
make coverage
```

### Code Quality
```bash
# Run all quality checks (lint, test, todo, black)
make all

# Lint code
make lint
# or
pyflakes *.py {tests,topologist,molior}/*.py {topologist,molior}/*/*.py

# Check code formatting
make black
# or
black --diff *.py {tests,topologist,molior}/

# Find TODOs and FIXMEs
make todo
```

## Architecture

### Three-Layer Design

The codebase is organized into three libraries that are designed to be platform-agnostic:

1. **topologist** - Extends topologic_core for building-specific geometry
   - Analyzes 3D CellComplex geometry to identify building components
   - Distinguishes horizontal faces (floors), vertical faces (walls), and other faces (roofs/soffits)
   - Decomposes geometry into **traces** (2D paths for walls, rooms, extrusions) and **hulls** (3D shells for roofs, soffits)
   - Contains graph implementations (`ugraph` for linear chains, `ushell` for faceted surfaces)
   - Handles topological relationships (adjacency, circulation) between rooms
   - **No knowledge of CAD/BIM/IFC** - purely geometric analysis

2. **molior** - Builds IFC models from topologist traces and hulls
   - Consumes traces and hulls from topologist
   - Uses IfcOpenShell to generate IFC building models
   - Implements building component modules: `Wall`, `Floor`, `Shell`, `Space`, `Stair`, `Extrusion`, `Repeat`, `Grillage`
   - Style system reads YAML configurations from `share/` directory
   - Handles structural analysis models and space boundaries
   - Main entry point: `Molior` class with factory methods `from_faces_and_widgets()`, `from_cellcomplex()`, `from_topology()`

3. **hmquery** - CLI tool for querying topology of homemaker-generated IFC files
   - Loads IFC files and reconstructs CellComplex via `Molior.get_cellcomplex_from_ifc()`
   - Subcommands: `cells`, `faces`, `adjacency`, `circulation`, `shortest-path`, `separation`
   - All output is JSON; queries cell properties, face classification, adjacency/circulation graphs, shortest paths, and centrality measures
   - Entry point: `hmquery <ifc_file> <subcommand> [options]`

4. **__init__.py** - Blender add-on integration
   - Provides Blender UI operators: `ObjectTopologise` (visualize topology), `ObjectHomemaker` (generate IFC)
   - Converts Blender mesh geometry to Topologic faces
   - Handles "widgets" (vertex objects named after room types like "bedroom", "kitchen") for cell usage assignment
   - Integrates with Bonsai BIM add-on via IfcStore

### Key Data Flow

```
Blender Mesh (faces + materials)
    ↓
Topologic Faces (with stylename attributes)
    ↓
CellComplex (3D geometry with cells/rooms)
    ↓
Traces + Hulls (2D paths + 3D shells, organized by style/condition/elevation)
    ↓
IFC Building Elements (walls, floors, spaces, etc.)
    ↓
IFC File (industry-standard BIM model)
```

### Style System

Building styles are defined in YAML files in the `share/` directory:
- **traces.yml** - Defines how 2D traces become walls, floors, extrusions, etc.
- **hulls.yml** - Defines how 3D hulls become roofs, soffits, etc.
- **openings.yml** - Window and door placement rules
- **families.yml** - Reusable component definitions
- **library.ifc** - IFC type library with predefined wall types, materials, etc.

Styles can be customized per subdirectory (e.g., `share/cinema/`, `share/fancy/`), with inheritance from parent definitions.

## Important Concepts

### Traces vs Hulls
- **Traces**: 2D linear paths (chains) defined at specific elevations with heights. Classified by condition (external, internal, open, etc.). Used for walls, floors, perimeters.
- **Hulls**: 3D faceted shells. Classified by condition (panel, soffit, etc.). Used for pitched roofs, curved surfaces.

### Conditions
Traces and hulls have "condition" attributes that determine their purpose:
- `external` - exterior walls facing outside
- `internal` - interior partition walls
- `open` - open edges (no solid wall, but may have columns/beams)
- `top-*` - roof/ceiling elements
- `bottom-*` - floor/foundation elements
- `panel` - roof panels
- `soffit` - ceiling soffits

### Topologic Index System
The software assigns index numbers to Cells (rooms), Faces, and Edges, then stores these in IFC property sets (`EPset_Topology`). This allows reconnecting IFC elements back to the topological model for:
- Space boundary assignment
- Structural member connections
- Regenerating IFC from stored topology

### Stashing Topology
When generating IFC, the original CellComplex is "stashed" in the IfcBuilding as:
- Tessellation representation (faces as IfcPolygonalFaceSet)
- Annotation elements (cell centroids with usage labels)
- FootPrint representation (2D building outline)

This allows `Molior.get_cellcomplex_from_ifc()` to reconstruct the CellComplex from an existing IFC file for regeneration.

## IFC Terminology

See `coding.md` for detailed IFC naming conventions. Key distinctions:
- **Entity**: Any IFC class instance
- **Object**: IfcObject subclass (rooted, has GlobalId)
- **Product**: IfcProduct subclass (has ObjectPlacement and Representation)
- **Element**: IfcElement subclass (physical building components like IfcWall)
- **Item**: Representation items (geometry, not rooted)

Use `ifcopenshell.api` (imported as `api`) for all IFC entity creation:
- `api.root.create_entity()` for rooted entities
- `api.geometry.assign_representation()` for geometry
- `api.spatial.assign_container()` for spatial relationships

## Dependencies

Core requirements (see `setup.py`):
- **topologic_core** - Python bindings to TopologicCore C++ library
- **ifcopenshell** - IFC file reading/writing
- **pyaml** (pyyaml) - YAML parsing for styles
- **numpy** - Numerical operations
- **shapely** - 2D geometry operations
- **bonsai** - Blender BIM add-on (Blender environment only)

The TopologicCore C++ library requires OpenCASCADE.

## Testing

Tests are in `tests/` (current) and `tests_old/` (legacy). Tests cover:
- Individual building components (walls, floors, spaces, etc.)
- IFC API usage and entity creation
- Geometric operations
- Style system and configuration parsing
- Topological analysis (adjacency, circulation, etc.)
- hmquery topology queries (`tests/test_hmquery.py`)

Use `pytest` configuration in `tests/pytest.ini`.

```bash
# Run all tests
pytest tests/

# Run hmquery tests only
pytest tests/test_hmquery.py -v
```

### hmquery Test Pattern

hmquery tests use the same two-stacked-cubes `cell_complex` fixture as `test_adjacency.py` (3 cells, 14 faces). Tests verify JSON serializability of all query results. The fixture does not allocate cell widgets, so all cells default to "living" or "void" usage.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
