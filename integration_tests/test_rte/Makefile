MY_MAKEFILES = Makefile.test_rte_during_run Makefile.test_rte_start Makefile.test_run_too_long Makefile.test_normal_binary

all: $(MY_MAKEFILES)
	for f in $(MY_MAKEFILES); do ("$(MAKE)" -f "$$f") || exit $$?; done

clean: $(MAKEFILES)
	for f in $(MY_MAKEFILES); do ("$(MAKE)" -f "$$f" clean) || exit $$?; done
