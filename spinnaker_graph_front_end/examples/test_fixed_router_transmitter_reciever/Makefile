all: hello_world.aplx hello_world_clone.aplx

%.aplx: %.Makefile %.c
	"$(MAKE)" -f $<

clean:
	for d in hello_world hello_world_clone ; do ("$(MAKE)" -f $$d.Makefile clean) || exit $$?; done

