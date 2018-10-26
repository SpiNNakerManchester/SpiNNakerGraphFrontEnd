BUILD_DIRS = test_fixed_router test_retransmission_phase_on_multi_cores hello_world \
 Conways speed_tracker speed_test_solo speed_tracker_with_protocol \
 speed_tracker_with_protocol_search test_extra_monitor_core_data_extraction \
 test_fixed_router_transmitter_reciever test_timer_setup_cost \
 test_extra_monitor_core_data_extraction_multiple_locations

all: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)") || exit $$?; done

clean: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)" clean) || exit $$?; done
