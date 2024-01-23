SANDBOX_IMAGE?=wireshark-sandbox:latest
WS_MOUNT?="$(PWD)/wireshark-lorawan-class-m"
# this directory is required to be mapped, otherwise git commands does not work (wireshark build process requires them to work)
GITMOD_MOUNT?="$(PWD)/../.git/modules/wireshark/wireshark-lorawan-class-m/"
CFG_MOUNT?="$(PWD)/config_wireshark"


all: docker-run

docker-build:
	@echo ".-=: Building docker sandbox image :=-."
	@if docker build -t $(SANDBOX_IMAGE) .; then \
printf "\n-- Docker image built. Run it with:\n\n  docker run -it --rm $(SANDBOX_IMAGE)\n" ; fi

docker-run: docker-build
	@echo ".-=: Starting docker sandbox image :=-."
	docker run -it -e DISPLAY=$(DISPLAY) -p 5555:5555/udp -v /tmp/.X11-unix:/tmp/.X11-unix -v$(CFG_MOUNT):/home/docker/.config/wireshark -v$(WS_MOUNT):/home/docker/wireshark/wireshark-lorawan-class-m -v$(GITMOD_MOUNT):/home/docker/.git/modules/wireshark/wireshark-lorawan-class-m $(SANDBOX_IMAGE)

clean:
	@echo ".-=: Removing docker sandbox image :=-."
	docker rmi $(SANDBOX_IMAGE)

