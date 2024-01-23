# ensure docker and docker-compose are available or install them e.g.:
https://docs.docker.com/engine/install/ubuntu/
sudo apt install docker-compose

# TODO: make this available from public docker repository so we need no access rights to this docker
# place config.json (email from Marek Novak) to ~/.docker directory

# test docker login
docker login docker.acrios.com

# install docker-compose

# manually pull wireguard-ssh docker image (without this process fails with "no basic auth credentials")
docker pull docker.acrios.com/acrios/wireguard-ssh

# build docker chirpstack-hash-generator
cd generateChirpstackPasswordHash
docker build -t chirpstack-hash-generator .
cd ..

# run docker-compose
sudo ./run.sh

# chirpstack is available at
CHIRPSTACK:
http://localhost:8080/
username: admin
password: astest

# database is available at
DATABASE: http://localhost:8081/
username: admin@acrios.com
password: sptest

# this command serves to delete all nonces from activation process
delete from public.device_activation
