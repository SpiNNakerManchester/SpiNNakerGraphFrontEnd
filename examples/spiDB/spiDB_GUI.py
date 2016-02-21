from Tkinter import *
import ScrolledText
import tkMessageBox
import tkFileDialog
from time import *
import sys
import pylab
import numpy as np

from spiDB_socket_connection import SpiDBSocketConnection

pylab.rc('xtick', labelsize=7)
pylab.rc('ytick', labelsize=7)

def highlight(e, scrolledText='input'):

    if scrolledText == 'input':
        scrolledText = queryScrolledText
        words = sql_keywords if currentDbTypeStringVar.get() == "SQL"\
                else kv_keywords
    elif scrolledText == 'output':
        scrolledText = outputText
        words = {'OK': ('', 'green'),
                 'FAIL': ('', 'red')}
    else:
        return

    for k, v in words.iteritems():
        start = '1.0'
        while start:
            start = scrolledText.search(k, start, END)
            if start:
                end = scrolledText.index('%s+%dc' % (start, len(k)))
                scrolledText.tag_add(k, start, end)
                scrolledText.tag_config(k,
                                         background=v[0],
                                         foreground=v[1])
                start = end

class MainMenu(Frame):
    def __init__(self, parent, textListener):
        Frame.__init__(self, parent)
        self.parent = parent
        self.textListener = textListener

        mbar = Menu(self.parent)
        self.parent.config(menu=mbar)

        self.fileMenu = Menu(mbar)

        mbar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.add_command(label="Open", command=self.onOpen)
        self.fileMenu.add_command(label="Quit", command=self.close)

        self.pingMenu = Menu(mbar)

        mbar.add_cascade(label="Ping", menu=self.pingMenu)

        self.pack(fill=BOTH, expand=1)

    def close(self):
        sys.exit(0)

    def onOpen(self):
        filespes = [('SQL file', '*.sql'),
                    ('KV file', '*.kv'),
                    ('CSV file', '*.csv'),
                    ('All files', '*')]
        dlg = tkFileDialog.Open(self, filetypes = filespes)
        fl = dlg.show()

        rf = self.readFile(fl)

        if not rf:
            return

        self.textListener.delete('1.0', END)
        self.textListener.insert(INSERT, rf)
        highlight(None)

    def readFile(self, filename):
        if not filename:
            return None
        try:
            f = open(filename, "r")
            return f.read()
        except Exception as e:
            return None

def emptyQueryPopup():
   tkMessageBox.showinfo("Query Error", "Cannot run empty query")

conn = SpiDBSocketConnection()
history = dict()

root = Tk()
root.title("SpiDB")

topFrame = Frame(root)
topFrame.pack(side=TOP, padx=5, pady=5)

bottomFrame = Frame(root)
bottomFrame.pack(side=BOTTOM)

leftFrame = Frame(bottomFrame)
leftFrame.pack(side=LEFT, padx=20, pady=20)

currentDbTypeStringVar = StringVar(topFrame)
currentDbTypeStringVar.set('Key-Value')
dbTypeMenu = OptionMenu(topFrame, currentDbTypeStringVar,
                        'Key-Value', 'SQL')

dbTypeMenu.config(font=('calibri',(12)),width=16)
dbTypeMenu['menu'].config(font=('calibri',(12)))

dbTypeMenu.pack(side=LEFT)

queryFrame = Frame(leftFrame)
queryFrame.pack(side=TOP, pady=(0,10))

historyFrame = Frame(leftFrame)
historyFrame.pack(side=BOTTOM)

rightFrame = Frame(bottomFrame)
rightFrame.pack(padx=20, pady=10)
rightFrame.pack(side=RIGHT)

queryLabel = Label(queryFrame, text="Query")
queryLabel.pack(side=TOP)

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
    master = historyFrame,
    width  = 40)
historyListbox.pack()

label = Label(rightFrame, text="Output")
label.pack(side=TOP)

outputText = ScrolledText.ScrolledText(
    master = rightFrame,
    wrap   = 'word',  # wrap text at full words only
    width  = 80,      # characters
    height = 30,      # text lines
    bg='white')

KEYWORD = ('', 'red')
OTHER = ('purple', 'white')
TYPE = ('', 'blue')

kv_keywords = {'.': OTHER,
               'CLEAR': OTHER, 'clear': OTHER,
               'put': KEYWORD, 'pull': KEYWORD,
               'PUT': KEYWORD, 'PULL': KEYWORD}

sql_keywords = {'.': OTHER,
                'CLEAR': OTHER, 'clear': OTHER,
                'varchar': TYPE, 'VARCHAR': TYPE,
                'integer': TYPE, 'INTEGER': TYPE,
                'SELECT': KEYWORD, 'select': KEYWORD,
                'FROM': KEYWORD, 'from': KEYWORD,
                'WHERE': KEYWORD, 'where': KEYWORD,
                'INSERT': KEYWORD, 'insert' : KEYWORD,
                'INTO': KEYWORD, 'into': KEYWORD,
                'VALUES': KEYWORD, 'values': KEYWORD,
                'CREATE': KEYWORD, 'create': KEYWORD,
                'TABLE': KEYWORD, 'table': KEYWORD}

queryScrolledText.bind('<Key>', highlight)


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

    outputText.delete('1.0', END)
    outputText.insert(INSERT, "Running...")

    error = True
    results = []

    #try:
    if currentDbTypeStringVar.get() == 'SQL':
        for stage in qText.split('.'):
            statements = [s.strip() for s in stage.split(';')]

            results.extend(conn.run(statements, 'SQL'))
    else:
        for stage in qText.split('.'):
                results.extend(conn.run(stage.split('\n'), 'Key-Value'))
    """except Exception as e:
        outputText.delete('1.0', END)
        outputText.insert(INSERT, e)
        return
    """

    s = ""
    xyp_occurences = dict()
    responseTimes = list()

    for r in results:
        if r is None:
            s += "No response\n"
        else:
            error = False
            s += "{}\n".format(str(r))

            for resp in r.responses:
                if resp.__xyp__() in xyp_occurences:
                    xyp_occurences[resp.__xyp__()] += 1
                else:
                    xyp_occurences[resp.__xyp__()] = 1
                responseTimes.append(resp.response_time)

    outputText.delete('1.0', END)
    outputText.insert(INSERT, s)
    highlight(None, scrolledText='output')

    queryResultTuple = (qText, s)

    t = strftime("%H:%M:%S", gmtime())
    qText = (qText[:truncateIndex] + '...')\
        if len(qText) > truncateIndex else qText
    qText = "{}  {}".format(t,qText)
    historyListbox.insert(0,qText)
    history[qText] = queryResultTuple

    if not error and len(responseTimes) > 1:
        pylab.figure()
        pylab.plot(range(len(responseTimes)), responseTimes)
        pylab.xlabel('Response')
        pylab.ylabel('ResponseTime')
        pylab.title('Response Times')

        tuples = xyp_occurences.keys()
        y_pos = np.arange(len(tuples))
        occurences = xyp_occurences.values()

        pylab.figure()
        pylab.bar(y_pos, occurences, align='center', alpha=0.5)
        pylab.xticks(y_pos, tuples)
        pylab.xlabel('Core')
        pylab.ylabel('Occurence')
        pylab.title('Usage by core')

        pylab.show()
    """
    except Exception as e:
        outputText.delete('1.0', END)
        outputText.insert(INSERT, e)
    """

menu = MainMenu(root,queryScrolledText)

pingsFailed = 0
connected = True
def ping():
    global connected
    global pingsFailed
    #threading.Timer(1,ping).start()
    p = conn.sendPing()
    menu.pingMenu.delete(12)
    if p is -1:
        menu.pingMenu.insert_command(index=0, label="PING FAILED", command=None)
        pingsFailed += 1
        if connected and pingsFailed is 2:
            connected = False
            tkMessageBox.showinfo("Ping failed", "Cannot connect to board")
    else:
        connected = True
        pingsFailed = 0
        menu.pingMenu.insert_command(index=0, label="PING {:.3f}ms".format(p), command=None)
    root.after(1000,ping)

runButton = Button(queryFrame, text="Run", fg="black", command=runQuery)
runButton.pack(side = RIGHT)

clearButton = Button(queryFrame, text="Clear", fg="black", command=clearQuery)
clearButton.pack(side = RIGHT)

#outputText.insert(INSERT, "Output text!")
#outputText.config(state=DISABLED)
outputText.pack()

#root.after(1000,ping) todo deactivated for now
root.mainloop()