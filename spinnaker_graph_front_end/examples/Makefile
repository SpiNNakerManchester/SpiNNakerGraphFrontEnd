BUILD_DIRS = test_retransmission_phase_on_multi_cores hello_world Conways speed_tracker speed_test_solo speed_tracker_with_protocol speed_tracker_with_protocol_search

all: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)") || exit $$?; done

clean: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)" clean) || exit $$?; done
