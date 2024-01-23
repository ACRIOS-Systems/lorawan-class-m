
simulator_install: apt_update device_install gateway_install localserver_install
	sudo apt install python3-pip
	pip3 install -r python/requirements.txt
	# start docker with localserver_instance, this needs to be the last as this is blocking forever
	$(MAKE) localserver_start

device_install:
	# jq is prerequisity for LoRaMac-node compile.sh script
	sudo apt install jq gcc g++ cmake
	cd device/LoRaMac-node; ./compile.sh

gateway_install:
	make -C gateway

chirpstack_install:
	echo "Not implemented yet"

localserver_install:
	# install docker only if the docker command is not available
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "docker is not installed. Installing Docker..."; \
		sudo apt install docker.io; \
	else \
		echo "Docker is already installed."; \
	fi

	# install docker-compose if it is not available
	@if ! command -v docker-compose >/dev/null 2>&1; then \
		echo "docker-compose is not installed. Installing docker-compose..."; \
		sudo apt install docker-compose; \
	else \
		echo "docker-compose is already installed."; \
	fi

	# build chirpstack-hash-generator - required for running local-server
	cd server/local-instance/generateChirpstackPasswordHash/; sudo docker build -t chirpstack-hash-generator .

localserver_start:
	cd server/local-instance/; sudo ./run.sh

localserver_stop:
	cd server/local-instance/; sudo ./reset.sh

apt_update:
	sudo apt update
