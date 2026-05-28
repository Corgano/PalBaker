import os
import shutil
import subprocess

def run_and_stream(cmd_args):
    """Executes a command and streams its output in absolute real-time to stdout."""
    process = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1 # Line-buffered
    )
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            if not line: break
            print(line.strip(), flush=True) 
            
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd_args)

def pack_cooked_assets(unrealpak_path: str, response_file: str, output_pak: str, folders_to_pack: list, has_anims: bool) -> int:
    """Creates the response file for UnrealPak and executes the packaging."""
    files_found = 0
    with open(response_file, "w") as f:
        for c_dir, v_path in folders_to_pack:
            if os.path.exists(c_dir):
                for root, _, files in os.walk(c_dir):
                    for file in files:
                        if file.endswith((".uasset", ".uexp", ".ubulk")):
                            # Exclude PhysicsAsset always
                            if "PhysicsAsset" in file:
                                continue
                            # Exclude Skeleton if no custom animations are shipped
                            if "Skeleton" in file and not has_anims:
                                continue
                                
                            abs_path = os.path.join(root, file)
                            rel_to_cooked = os.path.relpath(abs_path, c_dir)
                            rel_virtual = "../../../Pal/Content/" + v_path + "/" + rel_to_cooked.replace("\\", "/")
                            f.write(f'"{abs_path}" "{rel_virtual}"\n')
                            files_found += 1
                            
    if files_found > 0:
        run_and_stream([unrealpak_path, output_pak, f"-Create={response_file}"])
        
    return files_found