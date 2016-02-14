from Tkinter import *
import ScrolledText
import tkMessageBox
import tkFileDialog
from time import gmtime, strftime
import sys
import pylab
import numpy as np

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
        filespes = [('SQL file', '*.sql'),
                    ('Text file', '*.txt'),
                    ('All files', '*')]
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
    width  = 50,      # characters
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
    width  = 80,      # characters
    height = 30,      # text lines
    bg='white')

def onselect(evt):
    w = evt.widget
    if not w.curselection():
        return
    index = int(w.curselection()[0])
    value = w.get(index)

    queryScrolledText.delete('1.0',END)
    queryScrolledText.insert(INSERT, history[value][0])

    outputText.delete('1.0',END)
    outputText.insert(INSERT, history[value][1])

historyListbox.bind('<<ListboxSelect>>', onselect)

def clearQuery():
    queryScrolledText.delete('1.0',END)

def runQuery():
    truncateIndex = 30
    qText = queryScrolledText.get('1.0', 'end')

    if qText.isspace():
        emptyQueryPopup()
        return

    """
    pylab.figure()
    pylab.plot([1,2,3,4], [5,4,6,8])
    pylab.xlabel('Time/ms')
    pylab.ylabel('spikes')
    pylab.title('spikes')
    pylab.show()
    """

    outputText.delete('1.0',END)
    outputText.insert(INSERT, "Running...")

    error = False

    #try:
    results = conn.run(qText.split(';'))
    outputText.delete('1.0',END)

    s = ""
    xyp_occurences = dict()
    responseTimes = list()

    for r in results:
        if r is None:
            s += "No response\n"
        else:
            s += "{}\n".format(str(r))
            for resp in r.responses:
                if resp.__xyp__() in xyp_occurences:
                    xyp_occurences[resp.__xyp__()] += 1
                else:
                    xyp_occurences[resp.__xyp__()] = 1
                responseTimes.append(resp.response_time)
    print s

    outputText.insert(INSERT, s)

    """
    objects = tuple() #((0,0,1), (0,0,2), (0,0,3), (0,0,4), (0,0,5), (0,0,6))
    y_pos = np.arange(len(objects))
    performance = [10,8,6,4,2,1]

    pylab.bar(y_pos, performance, align='center', alpha=0.5)
    pylab.xticks(y_pos, objects)
    pylab.ylabel('Usage')
    pylab.title('Programming language usage')

    pylab.show()
    """
    #pylab.bar(range(len(xyp_occurences)), xyp_occurences.values(), align='center')
    #pylab.xticks(range(len(xyp_occurences)), xyp_occurences.keys())

    #pylab.show()

    """except Exception as e:
        s = "An error occured..."
        outputText.delete('1.0',END)
        outputText.insert(INSERT, s)
        error = True
    """
    queryResultTuple = (qText, s)

    t = strftime("%H:%M:%S", gmtime())
    qText = (qText[:truncateIndex] + '...')\
        if len(qText) > truncateIndex else qText
    qText = "{}  {}".format(t,qText)
    historyListbox.insert(0,qText)
    history[qText] = queryResultTuple

    if not error:
        pylab.figure()
        pylab.plot(range(len(responseTimes)), responseTimes)
        pylab.xlabel('Response')
        pylab.ylabel('ResponseTime')
        pylab.title('Response Times')
        pylab.show()

ex = FileOpener(root,queryScrolledText)

runButton = Button(queryFrame, text="Run", fg="black", command=runQuery)
runButton.pack(side = RIGHT)

clearButton = Button(queryFrame, text="Clear", fg="black", command=clearQuery)
clearButton.pack(side = RIGHT)

#outputText.insert(INSERT, "Output text!")
#outputText.config(state=DISABLED)
outputText.pack()

root.mainloop()




