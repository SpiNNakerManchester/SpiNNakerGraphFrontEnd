BUILD_DIRS = partitioned_example_a_no_vis_no_buffer partitioned_example_b_no_vis_buffer partitioned_example_c_vis_buffer q_partitionable r_partitionable

all: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)") || exit $$?; done

clean: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)" clean) || exit $$?; done
