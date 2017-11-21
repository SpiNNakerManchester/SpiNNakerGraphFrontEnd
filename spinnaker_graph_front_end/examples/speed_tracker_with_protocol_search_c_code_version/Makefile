all: packet_gatherer.aplx sdram_reader_and_transmitter_with_protocol.aplx

%.aplx: %.Makefile %.c
	"$(MAKE)" -f $<

clean:
	for d in packet_gatherer sdram_reader_and_transmitter_with_protocol; do ("$(MAKE)" -f $$d.Makefile clean) || exit $$?; done
    