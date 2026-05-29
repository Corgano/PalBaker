# utils/builder/log_analyzer.py
import flet as ft

class LogAnalyzer:
    def __init__(self):
        self.errors_encountered = []
        self.warnings_encountered = []
        
        # Diagnostic Knowledge Base
        self.rules = [
            # --- Unreal Engine Diagnostic Rules ---
            {
                "id": "missing_skeleton",
                "keywords": ["Invalid USkeleton supplied", "The skeleton asset for this animation Blueprint is missing"],
                "title": "Broken/Missing Skeleton Reference",
                "solution": "Unreal has dangling references to a deleted or renamed skeleton. Delete any old 'SK_*.uasset' files, delete the stale AnimBlueprints in your Content/Pal/Model/Character/Skeleton/ folder, and run 'Push to Unreal' again."
            },
            {
                "id": "unreal_connection_failed",
                "keywords": ["Unreal Editor is not running", "No response received from Unreal remote execution", "Connection refused"],
                "title": "Unreal Engine Connection Refused",
                "solution": "PalBaker could not establish a connection to Unreal Editor. Ensure your ModKit project is open in Unreal Editor and Python Remote Execution is enabled (Project Settings -> Python)."
            },
            {
                "id": "missing_import_package",
                "keywords": ["VerifyImport: Failed to load package", "Failed to load '/Game/", "Can't find file"],
                "title": "Missing Import Dependency / Stale References",
                "solution": "Your project contains references to deleted assets. Open Unreal Editor, right-click your Content folder, and select 'Fix Up Redirectors in Folder' to repair broken paths."
            },
            # --- Blender Diagnostic Rules ---
            {
                "id": "blender_psk_importer_missing",
                "keywords": ["No PSK importer addon/extension is registered", "No module named 'io_scene_psk_psa'", "No module named 'io_import_scene_unreal_psa_psk'"],
                "title": "Blender PSK Addon Missing",
                "solution": "Headless Blender failed to import the .psk file because the PSK Importer addon is not registered. Please install/enable the 'io_scene_psk_psa' extension in your Blender installation."
            },
            {
                "id": "blender_no_armature",
                "keywords": ["No armature found", "ERROR: No armature found"],
                "title": "Blender Rigging Error: Armature Missing",
                "solution": "Blender could not find any Armature inside your .blend file. Ensure your mesh has a valid armature modifier and bone structure named exactly 'Armature'."
            },
            {
                "id": "blender_path_invalid",
                "keywords": ["blender executed but failed to save", "failed to execute Blender process"],
                "title": "Invalid Blender Executable Path",
                "solution": "The Blender Executable Path configured in your Settings is invalid or inaccessible. Navigate to the Settings tab and set it to your actual 'blender.exe' file path."
            }
        ]

    def analyze_line(self, line: str) -> tuple[str, str, bool]:
        """
        Analyzes a log line, returns a formatted version, its Flet color, 
        and whether it is classified as a critical error.
        """
        line_lower = line.lower()
        is_error = False
        color = ft.Colors.WHITE70
        
        # Detect Unreal and Python errors
        if "error:" in line_lower or "critical error" in line_lower or "failed:" in line_lower or "traceback (most recent call last):" in line_lower:
            is_error = True
            color = ft.Colors.RED_400
            self.errors_encountered.append(line)
        # Detect warnings
        elif "warning:" in line_lower:
            color = ft.Colors.ORANGE_400
            self.warnings_encountered.append(line)
        # Detect progress stages
        elif ">>>" in line:
            color = ft.Colors.CYAN_400
        elif "success:" in line_lower:
            color = ft.Colors.GREEN_400

        # Scan against diagnostic rules to catch specific problems
        for rule in self.rules:
            for kw in rule["keywords"]:
                if kw.lower() in line_lower:
                    if rule not in self.errors_encountered:
                        self.errors_encountered.append(rule)

        return line, color, is_error

    def generate_summary(self, exit_success: bool) -> dict | None:
        """
        Builds a comprehensive diagnostic report if the process failed or 
        met matched errors.
        """
        if exit_success and not any(isinstance(err, dict) for err in self.errors_encountered):
            return None
            
        matched_issues = [err for err in self.errors_encountered if isinstance(err, dict)]
        
        return {
            "success": exit_success,
            "matched_rules": matched_issues,
            "total_warnings": len(self.warnings_encountered),
            "total_errors": len([e for e in self.errors_encountered if not isinstance(e, dict)])
        }