from Tkinter import *
import sys
from threading import Thread


class MainMenu(Frame):
    def __init__(self, parent, spinnaker):
        Frame.__init__(self, parent)
        self.parent = parent
        self._spinnaker = spinnaker

        mbar = Menu(self.parent)
        self.parent.config(menu=mbar)

        self.fileMenu = Menu(mbar)

        mbar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.add_command(label="Quit", command=self.close)

        self.pack(fill=BOTH, expand=1)

    def close(self):
        if self._spinnaker is not None:
            self._spinnaker.stop()
        sys.exit(0)


class GUIBuilder(Thread):

    def __init__(self, spinnaker):
        Thread.__init__(self, name="GUI builder thread")
        self.daemon = True
        self._spinnaker = spinnaker
        self._root = None
        self.start()

    def _build_gui(self):
        self._root = Tk()
        self._root.resizable(width=FALSE, height=FALSE)
        self._root.title("SpiDB_Server")

        top_frame = Frame(self._root)
        top_frame.pack(side=TOP, padx=5, pady=5)

        bottom_frame = Frame(self._root)
        bottom_frame.pack(side=BOTTOM)

        left_frame = Frame(bottom_frame)
        left_frame.pack(side=LEFT, padx=20, pady=20)

        query_frame = Frame(left_frame)
        query_frame.pack(side=TOP, pady=(0,10))

        history_frame = Frame(left_frame)
        history_frame.pack(side=BOTTOM)

        right_frame = Frame(bottom_frame)
        right_frame.pack(padx=20, pady=10)
        right_frame.pack(side=RIGHT)

        MainMenu(self._root, self._spinnaker)

    def run(self):
        self._build_gui()
        self._root.mainloop()

if __name__ == "__main__":
    GUIBuilder(None)
