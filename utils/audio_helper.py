# utils/audio_helper.py
import os
import json

SOUND_MAP_FILE = "resolved_sound_map.json"
_sound_map_cache = {}

# utils/audio_helper.py (Append to the end of the file)
def get_staged_audio_overrides(workspace) -> list[tuple[str, str]]:
    """Returns the list of absolute staged WEM source paths and their target virtual paths."""
    overrides = []
    if workspace.audio_media_dir and os.path.exists(workspace.audio_media_dir):
        for wem_file in os.listdir(workspace.audio_media_dir):
            if wem_file.endswith(".wem"):
                abs_wem = os.path.join(workspace.audio_media_dir, wem_file)
                virtual_wem = f"WwiseAudio/Media/{wem_file}"
                overrides.append((abs_wem, virtual_wem))
    return overrides

def load_sound_map() -> dict:
    """Loads and caches the resolved sound mapping structure."""
    global _sound_map_cache
    if _sound_map_cache:
        return _sound_map_cache
    
    # Locate resolved_sound_map.json in the repository root directory
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    map_path = os.path.join(repo_root, SOUND_MAP_FILE)
    
    if not os.path.exists(map_path):
        return {}
        
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            _sound_map_cache = json.load(f)
    except Exception as e:
        print(f"Error loading sound map: {e}")
        _sound_map_cache = {}
        
    return _sound_map_cache

def get_pal_sound_metadata(internal_name: str) -> dict:
    """
    Returns the mapped sounds dictionary for a specific Pal, 
    or an empty dict if the Pal does not have mapped cries.
    """
    sound_map = load_sound_map()
    return sound_map.get(internal_name, {})