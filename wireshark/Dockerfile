FROM ubuntu:22.04

RUN apt update && \
	apt install -y \
	git sudo

RUN adduser --disabled-password --gecos '' docker && \
    adduser docker sudo && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# to install everything without user interaction
ENV DEBIAN_FRONTEND=noninteractive

# copy debian-setup.sh in to docker container and install the dependencies
COPY wireshark-lorawan-class-m/tools/debian-setup.sh /home/docker/.
RUN /home/docker/debian-setup.sh --install-optional --install-deb-deps --install-test-deps -y

# clone wireshark and install dependencies
#RUN cd /home/docker && \
#    git clone https://gitlab.com/alpov/wireshark.git && \
#    cd wireshark/tools && \
#    ./debian-setup.sh --install-optional --install-deb-deps --install-test-deps -y

# build wireshark
#RUN mkdir /home/docker/wireshark/build && \
#    cd /home/docker/wireshark/build && \
#    cmake .. && \
#    make -j8

#RUN cd /home/docker/wireshark/build && \
#    git pull && \
#    git checkout -b lora origin/lora && \
#    make -j8

#COPY wireshark-lorawan-class-m /home/docker/wireshark-classM


USER docker
ENV HOME /home/docker
WORKDIR /home/docker

COPY startup.sh /bin/startup.sh

ENTRYPOINT ["/bin/startup.sh"]
