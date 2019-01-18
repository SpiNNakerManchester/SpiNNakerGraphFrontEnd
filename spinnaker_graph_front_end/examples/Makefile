BUILD_DIRS = test_fixed_router hello_world Conways test_extra_monitor \
 test_fixed_router_transmitter_reciever test_timer_setup_cost
all: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)") || exit $$?; done

clean: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)" clean) || exit $$?; done
