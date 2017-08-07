BUILD_DIRS = hello_world Conways speed_tracker speed_test_solo

all: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)") || exit $$?; done

clean: $(BUILD_DIRS)
	for d in $(BUILD_DIRS); do (cd $$d; "$(MAKE)" clean) || exit $$?; done
