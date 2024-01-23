
all: libloragw.a lora_pkt_fwd
	@echo "All Compiled!"

libloragw.a:
	make -C lora_gateway/libloragw

lora_pkt_fwd:
	make -C packet_forwarder/lora_pkt_fwd

install:
	apt install gcc
