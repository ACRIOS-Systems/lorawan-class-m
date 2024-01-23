#!/bin/sh

docker build -t chirpstack-hash-generator . 2> /dev/null 1> /dev/null
docker run -e INPUT="$1" chirpstack-hash-generator
