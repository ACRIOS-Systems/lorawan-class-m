make build_debug
/go/bin/dlv --listen=:4000 --headless=true --log=true --accept-multiclient --api-version=2 exec build/chirpstack-network-server