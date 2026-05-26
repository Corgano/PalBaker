# PalBaker (Palworld Mod Manager)

A dedicated, automated modding environment for Palworld that handles the pipeline from raw FModel extracts to a fully cooked and packed `_P.pak` file. It orchestrates Blender, Unreal Engine 5.1, and UnrealPak using a Flet-based UI.

## Features
* **State Tracking:** Detects whether a mod is in a raw state, has active source files (.blend), contains compiled Unreal Engine assets, or has been manually modified inside the Unreal Editor.
* **Context-Aware Pipeline:** Offers specific actions based on the mod's current state (Push to Unreal, Cook & Pack, or Full Pipeline).
* **Headless Blender Integration:** Automatically converts `.blend` files to `.fbx` with forced bone scaling, rotation, and hierarchy parameters compatible with Palworld's physics limits.
* **Unreal Engine Remote Execution:** Injects asset serialization commands directly into a running Unreal Editor instance, avoiding engine cold-boot times.
* **Targeted Micro-Cooking:** Temporarily overrides `DefaultGame.ini` to restrict the Unreal Cooker to the specific mod folder and skeleton directory, reducing cook times from minutes to seconds.
* **Safe Packaging:** Automatically filters out generated skeletons and physics assets during the packaging phase to prevent in-game ragdoll glitches.
* **Real-Time Progress Tracking:** Parses Python subprocess stdout streams unbuffered to provide a real-time UI progress bar and status console.

## Prerequisites
1. Python 3.10+
2. `flet` (v0.85.0+)
3. Unreal Engine 5.1
4. Palworld ModKit (`.uproject`)
5. Blender
6. FModel (for initial asset extraction)

## Setup
1. Clone or place this repository in a dedicated directory.
2. Ensure the `pal_names_map.json` file is located in the root of the project.
3. Install dependencies: `pip install flet`
4. Run the manager: `python manager.py`
5. Navigate to the **Settings** tab and configure the executable and directory paths.

## Usage
* Enable **Remote Execution** in your Unreal Engine Project Settings -> Python.
* Keep the Unreal Editor open.
* Use the UI to select a mod and execute the relevant build pipeline phase.