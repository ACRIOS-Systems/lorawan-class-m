#!/bin/bash

#export CROSS_COMPILE=arm-linux-gnueabihf-

#cd /pitaya

# Clone RedPitaya Ecosystem
#[ ! -d "RedPitaya" ] && git clone $PITAYA_REPO

# Download and build linux kernel for the first time
#if [ ! -d "RedPitaya/tmp" ]
#then
#	cd RedPitaya
#	source settings.sh
#	make -f Makefile.x86 linux
#fi

# copy wireshark persistent preferences
cd /home/docker
mkdir -p .config/wireshark
ln -s config_wireshark/preferences .config/wireshark/preferences

# build or rebuild the wireskark
mkdir /home/docker/wireshark/wireshark-lorawan-class-m/build
cd /home/docker/wireshark/wireshark-lorawan-class-m/build
cmake ..
make -j8

# run wireshark and start capture with udpdump
/home/docker/wireshark/wireshark-lorawan-class-m/build/run/wireshark -i udpdump -k
bash
