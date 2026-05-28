import sys
import os
import time

def run_remote_import(ue_root: str, project_name: str, fmodel_dir: str, ue_script_path: str) -> tuple[bool, str]:
    """Establishes a remote execution socket connection with the Unreal Editor and runs the importer."""
    ue_python_dir = os.path.join(ue_root, "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python")
    sys.path.append(ue_python_dir)
    
    try:
        import remote_execution  # type: ignore
    except ImportError:
        return False, "Could not find remote_execution.py in Unreal installation directory."

    remote_exec = remote_execution.RemoteExecution()
    remote_exec.start()
    time.sleep(2.0)
    
    node = next((n for n in remote_exec.remote_nodes if n.get('project_name', '').lower() == project_name.lower()), None)
    if not node:
        remote_exec.stop()
        return False, "Unreal Editor is not running. Please open your project first."
        
    remote_exec.open_command_connection(node.get('node_id'))
    
    palbaker_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")).replace("\\", "/")
    ue_script_path_clean = ue_script_path.replace("\\", "/")
    
    cmd = f'TARGET_FOLDER = r"{fmodel_dir}"; PALBAKER_ROOT = r"{palbaker_root}"; exec(open(r"{ue_script_path_clean}").read())'
    
    print("Injecting import commands into Unreal Editor...")
    response = remote_exec.run_command(cmd)
    remote_exec.stop()

    logs = []
    if response is not None:
        if response.get('output'):
            for log_entry in response['output']:
                log_text = log_entry.get('output', '') if isinstance(log_entry, dict) else str(log_entry)
                if log_text.strip():
                    logs.append(log_text.rstrip())
                    
        success = response.get('success', False)
        result_msg = "\n".join(logs)
        if not success:
            result_msg += f"\nError Details: {response.get('result')}"
        return success, result_msg
    else:
        return False, "No response received from Unreal remote execution."