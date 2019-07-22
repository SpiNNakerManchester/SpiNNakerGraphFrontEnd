#APPS = const_scalar.mk const_tensor.mk const_float_tensor.mk add.mk mul.mk mat_mul.mk mat_mul_float.mk const_tensor_non_dynamic.mk mat_mul_non_dynamic.mk add_broadcast_nd.mk mat_mul_non_dynamic.mk
#APPS = const_tensor_non_dynamic.mk  mat_mul_non_dynamic.mk  add_broadcast_nd.mk mul_broadcast_nd.mk
APPS = const_scalar.mk fill.mk const_empty.mk neg_scalar.mk

all: $(APPS)
	for f in $(APPS); do $(MAKE) -f $$f || exit $$?; done

%.aplx: %.mk
	"$(MAKE)" -f $*

clean: $(DIRS)
	for f in $(APPS); do $(MAKE) -f $$f clean || exit $$?; done