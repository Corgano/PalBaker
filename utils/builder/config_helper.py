import os

def inject_packaging_settings(ini_path: str, ue_virtual_path: str, skeleton_virtual_path: str, anims_virtual_path: str, has_anims: bool):
    """Safely updates DefaultGame.ini packaging settings without modifying existing user entries."""
    if not os.path.exists(ini_path):
        return
        
    with open(ini_path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()
        
    new_lines = []
    in_section = False
    section_found = False
    section_header = "[/Script/UnrealEd.ProjectPackagingSettings]"
    
    keys_to_override = [
        "DirectoriesToAlwaysCook", "+DirectoriesToAlwaysCook", "-DirectoriesToAlwaysCook",
        "bCookAll", "bUseIoStore", "bShareMaterialShaderCode", "MapsToCook", "+MapsToCook", "-MapsToCook"
    ]
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped.lower() == section_header.lower():
                in_section = True
                section_found = True
                new_lines.append(line)
                new_lines.append("bCookAll=False\n")
                new_lines.append("bUseIoStore=False\n")
                new_lines.append("bShareMaterialShaderCode=False\n")
                new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{ue_virtual_path}")\n')
                new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{skeleton_virtual_path}")\n')
                if has_anims:
                    new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{anims_virtual_path}")\n')
                new_lines.append("MapsToCook=\n")
                continue
            else:
                in_section = False
                
        if in_section:
            if any(stripped.startswith(k) for k in keys_to_override):
                continue
        new_lines.append(line)
        
    if not section_found:
        new_lines.append("\n" + section_header + "\n")
        new_lines.append("bCookAll=False\n")
        new_lines.append("bUseIoStore=False\n")
        new_lines.append("bShareMaterialShaderCode=False\n")
        new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{ue_virtual_path}")\n')
        new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{skeleton_virtual_path}")\n')
        if has_anims:
            new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{anims_virtual_path}")\n')
        
    with open(ini_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)