#!/bin/bash
cd "$(dirname "$0")"
curl -X POST http://localhost:8050/meshvis/api/device -H 'Content-Type: application/json' -d @sample-devices.json