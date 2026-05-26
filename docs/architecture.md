# Architecture

The application is divided into a frontend UI (Flet) and a backend orchestration layer (subprocess and Unreal Python API).

## Directory Structure
* `manager.py`: The entry point for the UI.
* `build_mod.py`: The backend orchestrator executed as an unbuffered subprocess.
* `ue_import.py`: The script executed internally by Unreal Engine via remote execution.
* `components/`: Flet UI definitions.
* `utils/`: File I/O, state tracking, and parsing logic.

## Pipeline Flow
1. **Blender Export:** `build_mod.py` calls `blender.exe` in background mode. It executes a Python expression to export the `.blend` file to `.fbx`. `global_scale=0.01` and `apply_scale_options='FBX_SCALE_ALL'` are enforced to fix standard Unreal Engine bone scaling issues. `add_leaf_bones=False` prevents hierarchy corruption.
2. **Unreal Engine Injection:** `build_mod.py` establishes a remote connection to the open Unreal Editor. It passes the target directory as a variable and executes the text content of `ue_import.py`.
3. **Asset Serialization (`ue_import.py`):**
    * Existing assets are wiped from the cache.
    * Textures are imported.
    * The `.fbx` is imported without generating standard materials, but forcing physics asset generation.
    * Material Instances are constructed from parsed JSON files and assigned specific parent materials based on naming conventions.
    * Skeletons and Physics Assets are relocated and renamed to match Palworld's expected path structures.
    * Materials are linked to the skeletal mesh slots.
4. **Cooking:** `build_mod.py` modifies the Unreal Project's `DefaultGame.ini` to point `DirectoriesToAlwaysCook` strictly to the target folder and its associated skeleton folder. `UnrealEditor-Cmd.exe` is called with `-run=cook` and `-Map=/Engine/Maps/Entry` to perform a targeted cook.
5. **Packaging:** `UnrealPak.exe` is called. The script iterates through the cooked directory, explicitly excluding `.uasset`, `.uexp`, and `.ubulk` files matching `Skeleton` or `PhysicsAsset`. The output is deposited into the designated target folder or the game's `Paks/palBaker` directory.