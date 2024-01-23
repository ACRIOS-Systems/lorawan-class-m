#!/bin/bash

JSON_FILE=".vscode/settings.json"
BUILD_DIR="build"

##
## CMake parameters extraction from .vscode/settings.json
##

# first CMake parameters are extracted from json file
# and later these parameters are used to build a device for the simulator

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "Error: jq could not be found. Please install jq. e.g.:"
    echo "sudo apt install jq"
    exit 1
fi

# Remove comments and save to a temporary file
TEMP_FILE=$(mktemp)

# Remove lines starting with comments and strip inline comments
sed -e '/^\s*\/\/.*/d' -e 's/\s*\/\/.*//' $JSON_FILE > $TEMP_FILE

# Extract cmake options
CMAKE_OPTIONS=$(jq -r '.["cmake.configureSettings"] | to_entries | map("-D\(.key)=\(.value)") | join(" ")' $TEMP_FILE)

# Print extracted options (or pass them directly to cmake)
echo "CMake options:"
echo $CMAKE_OPTIONS

# Remove the temporary file
rm -f $TEMP_FILE

##
## Cmake part
##

# create build directory
mkdir -p $BUILD_DIR
cd $BUILD_DIR

# run CMake
cmake --no-warn-unused-cli $CMAKE_OPTIONS -DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=TRUE -DCMAKE_C_COMPILER:FILEPATH=/usr/bin/gcc -DCMAKE_CXX_COMPILER:FILEPATH=/usr/bin/g++ ..

# run compilation
make -j8

# copy periodic uplink to build directory
cp src/apps/LoRaMac/LoRaMac-periodic-uplink-lpp .
