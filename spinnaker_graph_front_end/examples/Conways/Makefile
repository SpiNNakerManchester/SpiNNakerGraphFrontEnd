BUILD_DIRS = partitioned_example_a_no_vis_no_buffer partitioned_example_b_no_vis_buffer

all: $(BUILD_DIRS)
	@for d in $(BUILD_DIRS); do "$(MAKE)" -C $$d || exit $$?; done

clean: $(BUILD_DIRS)
	@for d in $(BUILD_DIRS); do "$(MAKE)" -C $$d clean || exit $$?; done
