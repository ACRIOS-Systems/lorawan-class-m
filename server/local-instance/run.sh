#!/bin/bash

echo "Automation for backend and frontend deployment & docker-compose"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root - run with sudo and think twice you are doing the right thing!" 
   exit 1
fi

# remove if already up
docker-compose down --remove-orphans

# load environment variables for this instance
source .env

# create network proxy
docker network create proxy

# start it
docker-compose up --build -d

# wait for gwbridge - set route
echo "Wait for gateway bridge to be up"
until [ "`docker inspect -f {{.State.Running}} ${DOCKER_PREFIX}_chirpstack-gateway-bridge_1`"=="true" ]; do
    sleep 0.1;
done;
echo "Add static route for gateway bridge to be able to get to VPN network"
docker-compose exec --privileged --user root chirpstack-gateway-bridge sh -c "ip r add 10.${INST_NET_NUM}.255.0/24 via 172.${INST_NET_NUM}.255.250"

# if not done, change initial admin password of chirpstack application server
AS_ADMIN_PWD_CHANGED_FLAG_FILE="data/postgre/chirpstack_as_admin_pwd_changed"
if [ ! -f "${AS_ADMIN_PWD_CHANGED_FLAG_FILE}" ]; then
    echo "Chirpstack application server admin password not changed, change now..."
    echo "Wait for chirpstack application server to be up and initialize the database..."
    until [ "`docker inspect -f {{.State.Running}} ${DOCKER_PREFIX}_chirpstack-application-server_1`"=="true" ]; do
        sleep 0.1;
    done;

    echo "Chirpstack app server is up, wait for it to create the database..."
    sleep 30 # ugly, but works...

    while true; do
        RESULT=$(docker exec -it ${DOCKER_PREFIX}_postgresql_1 /bin/bash -c "`bash generateChirpstackPasswordHash/generate.sh ${AS_PASSWORD}`")
        if [[ "$RESULT" == *"UPDATE 1"* ]]; then
            break
        fi
        sleep 10
        echo "try again..."
    done

    echo "generation done!"
    touch "${AS_ADMIN_PWD_CHANGED_FLAG_FILE}"
    echo "running..."
fi



# start logs to see what happens - user can safely kill this without stopping the docker-compose
docker-compose logs -f
