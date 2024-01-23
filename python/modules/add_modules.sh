#!/bin/bash

# Unique environment variable to check if the script has already run
if [ "$ADD_MODULES_SCRIPT_RUN" == "true" ]; then
    echo "The script has already been run. Exiting."
    return
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Initialize PYTHONPATH with the current value if it exists, or as an empty string if it does not
PYTHONPATH="${PYTHONPATH:-}"

# Loop through all subdirectories of the script's directory
for MODULE_DIR in "$SCRIPT_DIR"/*; do
    # Check if the item is a directory
    if [ -d "$MODULE_DIR" ]; then
        # If PYTHONPATH is empty, set it to the directory, else append the directory to it
        if [ -z "$PYTHONPATH" ]; then
            PYTHONPATH="$MODULE_DIR"
        else
            PYTHONPATH="$PYTHONPATH:$MODULE_DIR"
        fi
    fi
done

# Export the updated PYTHONPATH
export PYTHONPATH

# Set the unique environment variable to true to indicate that the script has run
export ADD_MODULES_SCRIPT_RUN=true

# Optionally, print the updated PYTHONPATH
echo "$PYTHONPATH"
