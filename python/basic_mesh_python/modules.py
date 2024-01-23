import sys
import os
import subprocess


def find_script_path():
    """Find the path of the add_modules.sh script from a list of potential locations."""
    script_paths = [
        '../modules/add_modules.sh',
        './modules/add_modules.sh',
        './python/modules/add_modules.sh'
    ]

    for script_path in script_paths:
        if os.path.exists(script_path):
            return script_path
    return None



# Attempt to import the lora_sim_lib
try:
    import lora_sim_lib
except ImportError:
    # if the import fails, we lora_sim_lib is not installed and is not on path
    # execute the add_module.sh script - its output needs to be added to python path
    add_modules_path = find_script_path()
    result = subprocess.run([add_modules_path], capture_output=True, text=True)
    # results needs to be stripped and split by ":" as this is bash format of separating the paths
    module_paths = result.stdout.strip().split(":")

    # add each path to path
    for path in module_paths:
        if path not in sys.path:
            sys.path.append(path)

    # print the updated path
    print("lora_sim_lib not found, updating PATH:", sys.path)
