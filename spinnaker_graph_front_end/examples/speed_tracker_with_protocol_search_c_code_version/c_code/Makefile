OBJECTS = host_data_receiver.o UDPConnection.o

APP = host_data_receiver

UNAME_S := $(shell uname -s)
ifeq ($(findstring MINGW, $(UNAME_S)), MINGW)
    CPPFLAGS += -D FREEGLUT_STATIC
    LIBS += -lfreeglut_static -lopengl32 -lwinmm -lgdi32 -lglu32
endif
ifeq ($(UNAME_S), Darwin)
    LIBS += -framework OpenGL -framework GLUT
endif
ifeq ($(UNAME_S), Linux)
    LIBS += -lGL -lGLU -lglut
endif

all: $(APP)
$(APP): $(OBJECTS)
	g++ -o $@ $< $(LIBS)
