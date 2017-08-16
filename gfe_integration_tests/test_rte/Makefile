MY_MAKEFILES = test_rte_during_run.mk test_rte_start.mk test_run_too_long.mk

all: $(MY_MAKEFILES)
	for f in $(MY_MAKEFILES); do \
		$(MAKE) -f $$f || exit $$?; \
	done

clean: $(MAKEFILES)
	for f in $(MY_MAKEFILES); do \
		$(MAKE) -f $$f clean || exit $$?; \
	done
