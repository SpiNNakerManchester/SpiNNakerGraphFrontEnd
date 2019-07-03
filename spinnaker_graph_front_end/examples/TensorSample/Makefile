APPS = const_scalar.mk const_tensor.mk add.mk mul.mk mat_mul.mk

all: $(APPS)
	for f in $(APPS); do $(MAKE) -f $$f || exit $$?; done

%.aplx: %.mk
	"$(MAKE)" -f $*

clean: $(DIRS)
	for f in $(APPS); do $(MAKE) -f $$f clean || exit $$?; done