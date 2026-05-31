# utils/builder/blender_helper.py
import os
import subprocess

def run_headless_blender(blender_path: str, blend_file: str | None, script_path: str, args: list) -> subprocess.CompletedProcess:
    """Executes a script inside headless Blender, loading startup files, enabling addons via CLI, and capturing output."""
    cmd = [blender_path, "-b"]
    
    if blend_file and blend_file.lower().endswith(".blend"):
        cmd.append(blend_file)
        
    # Force Blender to natively load and enable the PSK extensions/addons on boot
    cmd.extend([
        "--addons", 
        "bl_ext.blender_org.io_scene_psk_psa,bl_ext.user_default.io_scene_psk_psa,io_scene_psk_psa,io_import_scene_unreal_psa_psk"
    ])
    
    cmd.extend(["--python", script_path, "--"])
    cmd.extend(args)
    
    # Capture output natively with automatic UTF-8 fallback
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')