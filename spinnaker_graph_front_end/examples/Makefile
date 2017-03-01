BUILD_DIRS = hello_world Conways

all: $(BUILD_DIRS)
	@for d in $(BUILD_DIRS); do "$(MAKE)" -C $$d || exit $$?; done

clean: $(BUILD_DIRS)
	@for d in $(BUILD_DIRS); do "$(MAKE)" -C $$d clean || exit $$?; done
