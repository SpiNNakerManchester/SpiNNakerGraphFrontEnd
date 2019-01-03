all: packet_gatherer.aplx sdram_reader_and_transmitter.aplx

%.aplx: %.Makefile src/%.c
	"$(MAKE)" -f $<

clean:
	for d in packet_gatherer sdram_reader_and_transmitter; do ("$(MAKE)" -f $$d.Makefile clean) || exit $$?; done
    