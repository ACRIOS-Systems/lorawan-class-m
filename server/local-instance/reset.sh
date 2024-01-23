#!/bin/bash

echo "Reset to default state, removing all data and keeping configuration"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root - run with sudo and think twice you are doing the right thing!" 
   exit 1
fi


# stop it
docker-compose down

# remove data folder
rm -rf data || true
