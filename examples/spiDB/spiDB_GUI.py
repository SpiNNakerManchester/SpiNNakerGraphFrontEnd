from Tkinter import *
import ScrolledText
import tkMessageBox
import tkFileDialog
from time import gmtime, strftime
import sys

from spiDB_socket_connection import SpiDBSocketConnection

class FileOpener(Frame):
    def __init__(self, parent, textListener):
        Frame.__init__(self, parent)
        self.parent = parent
        self.textListener = textListener

        mbar = Menu(self.parent)
        self.parent.config(menu=mbar)
        fMenu = Menu(mbar)

        mbar.add_cascade(label="File", menu=fMenu)
        fMenu.add_command(label="Open", command=self.onOpen)
        fMenu.add_command(label="Exit", command=self.close)

        self.pack(fill=BOTH, expand=1)

    def close(self):
        sys.exit(0)

    def onOpen(self):
        filespes = [('All files', '*'),
                    ('SQL file', '*.sql'),
                    ('Text file', '*.txt')]
        dlg = tkFileDialog.Open(self, filetypes = filespes)
        fl = dlg.show()

        self.textListener.delete('1.0', END)
        self.textListener.insert(INSERT, self.readFile(fl))

    def readFile(self, filename):
        f = open(filename, "r")
        return f.read()

def emptyQueryPopup():
   tkMessageBox.showinfo("Query Error", "Cannot run empty query")

conn = SpiDBSocketConnection()
history = dict()

root = Tk()
root.title("SpiDB")

leftFrame = Frame(root)
leftFrame.pack(side=LEFT, padx=20, pady=20)

queryFrame = Frame(leftFrame)
queryFrame.pack(side=TOP, pady=(0,10))

historyFrame = Frame(leftFrame)
historyFrame.pack(side=BOTTOM)

rightFrame = Frame(root)
rightFrame.pack(padx=20, pady=10)
rightFrame.pack(side=RIGHT)

label = Label(queryFrame, text="Query")
label.pack(side=TOP)

queryScrolledText = ScrolledText.ScrolledText(
    master = queryFrame,
    wrap   = 'word',  # wrap text at full words only
    width  = 60,      # characters
    height = 15,      # text lines
    bg='white')
queryScrolledText.pack(side=TOP)

label = Label(historyFrame, text="History")
label.pack(side=TOP)

historyListbox = Listbox(
    master=historyFrame,
    width  = 40)
historyListbox.pack()

label = Label(rightFrame, text="Output")
label.pack(side=TOP)

outputText = Text(
    master = rightFrame,
    wrap   = 'word',  # wrap text at full words only
    width  = 100,      # characters
    height = 30,      # text lines
    bg='white')

def onselect(evt):
    w = evt.widget
    if not w.curselection():
        return
    index = int(w.curselection()[0])
    value = w.get(index)
    outputText.delete('1.0',END)
    outputText.insert(INSERT, history[value])

historyListbox.bind('<<ListboxSelect>>', onselect)

def clearQuery():
    queryScrolledText.delete('1.0',END)

def runQuery():
    truncateIndex = 30
    qText = queryScrolledText.get('1.0', 'end')

    if qText.isspace():
        emptyQueryPopup()
        return

    outputText.delete('1.0',END)
    outputText.insert(INSERT, "Running...")

    try:
        result = conn.run([qText])[0]
        outputText.delete('1.0',END)
        outputText.insert(INSERT, str(result))
    except Exception:
        result = "An error occured..."
        outputText.delete('1.0',END)
        outputText.insert(INSERT, result)

    t = strftime("%H:%M:%S", gmtime())
    qText = (qText[:truncateIndex] + '...')\
        if len(qText) > truncateIndex else qText
    qText = "{}  {}".format(t,qText)
    historyListbox.insert(0,qText)
    history[qText] = str(result)

ex = FileOpener(root,queryScrolledText)

runButton = Button(queryFrame, text="Run", fg="black", command=runQuery)
runButton.pack(side = RIGHT)

clearButton = Button(queryFrame, text="Clear", fg="black", command=clearQuery)
clearButton.pack(side = RIGHT)

#outputText.insert(INSERT, "Output text!")
#outputText.config(state=DISABLED)
outputText.pack()

root.mainloop()




