from Tkinter import *
import ScrolledText
import tkMessageBox
import tkFileDialog
from time import *
import sys
import pylab
import numpy as np
import matplotlib.ticker as ticker

from spiDB_socket_connection import SpiDBSocketConnection

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
        filespes = [('KV file', '*.kv'),
                    ('SQL file', '*.sql'),
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
    global pausePing
    pausePing = True
    truncateIndex = 30
    qText = queryScrolledText.get('1.0', 'end')

    if qText.isspace():
        emptyQueryPopup()
        return

    outputText.delete('1.0', END)
    outputText.insert(INSERT, "Running...")

    error = True
    results = []
    downloads = list()
    uploads = list()

    #ms
    totalDownloadTime = 0
    totalUploadTime = 0

    packetsSent = 0
    packetsReceived = 0

    #try:
    if currentDbTypeStringVar.get() == 'SQL':
        for stage in qText.split('.'):
            statements = [s.strip() for s in stage.split(';')]

            r = conn.run(statements, 'SQL')

            results.extend(r["results"])
            downloads.extend(r["download"])
            uploads.extend(r["upload"])
            totalUploadTime += r["uploadTime"]
            totalDownloadTime += r["downloadTime"]
            packetsSent += r["packetsSent"]
            packetsReceived += r["packetsReceived"]
    else:
        for stage in qText.split('.'):
            r = conn.run(stage.split('\n'), 'Key-Value')

            results.extend(r["results"])
            downloads.extend(r["download"])
            uploads.extend(r["upload"])
            totalUploadTime += r["uploadTime"]
            totalDownloadTime += r["downloadTime"]
            packetsSent += r["packetsSent"]
            packetsReceived += r["packetsReceived"]

    pausePing = False
    """except Exception as e:
        outputText.delete('1.0', END)
        outputText.insert(INSERT, e)
        return
    """

    xyp_occurences = dict()
    xyp_bytes = dict()
    responseTimes = list()
    occ = [[[0 for p in range(18)] for y in range(2)] for x in range(2)]

    totalResponseTimesAddedUp = 0
    packetsUnreplied = 0
    for r in results:
        if r is None:
            packetsUnreplied += 1
        else:
            if not r.responses:
                packetsUnreplied += 1
            else:
                for resp in r.responses:
                    if resp.__xyp__() in xyp_occurences:
                        xyp_occurences[resp.__xyp__()] += 1
                        if resp.cmd == "PUT":
                            xyp_bytes[resp.__xyp__()] += resp.data
                    else:
                        xyp_occurences[resp.__xyp__()] = 1
                        if resp.cmd == "PUT":
                            xyp_bytes[resp.__xyp__()] = resp.data
                    responseTimes.append(resp.response_time)
                    totalResponseTimesAddedUp += resp.response_time

    for xyp, o in xyp_occurences.iteritems():
        (x, y, p) = xyp
        occ[x][y][p] = o

    s = "Statistics:\n\n" \
        "  total upload time:      {:>11}\n"\
        "  total download time:    {:>11}\n\n"\
        "  average response time:  {:.3f}ms\n\n"\
        "  number of packets sent:               {:>6} {:>12}\n"\
        "  number of packets received:           {:>6} {:>12}\n"\
        "  number of packets unreplied or lost:  {:>6}\n\n"\
        .format("{:.2f}ms".format(totalUploadTime),
                "{:.2f}ms".format(totalDownloadTime),
                totalResponseTimesAddedUp/packetsReceived,
                packetsSent, "({} bytes)".format(sum([x[1] for x in uploads])),
                packetsReceived, "({} bytes)".format(sum([x[1] for x in downloads])),
                packetsUnreplied)

    for r in results:
        if r is None:
            s += "No response\n"
        else:
            error = False
            s += "{}\n".format(str(r))

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

    if not error and len(responseTimes) > 2:
        #########################################################

        xUpload = [x[0] for x in uploads]
        yUpload = [x[1] for x in uploads]

        xDownload = [x[0] for x in downloads]
        yDownload = [x[1] for x in downloads]

        pylab.figure()
        fig = pylab.gcf()
        fig.canvas.set_window_title('Network Traffic')
        pylab.plot(xUpload, yUpload, label='upload')
        pylab.plot(xDownload, yDownload, label='download')
        pylab.legend(loc='upper left')
        pylab.xlabel('Query ID')
        pylab.ylabel('Bytes')
        pylab.title('Network Traffic')

        ####################################################################
        pylab.figure()
        fig = pylab.gcf()
        fig.canvas.set_window_title('Response Times')

        x = range(len(responseTimes))
        y = responseTimes
        pylab.ylim([0, max(1, max(responseTimes)+0.1)])
        pylab.plot(x, y, 'bo', label='sample')

        pylab.plot(x, np.poly1d(np.polyfit(x, y, 5))(x), 'r', label='fitting')
        #pylab.plot(1, fit[0] * 1 + fit[1], color='red')
        #pylab.plot(range(len(responseTimes)), responseTimes,
        #           ':k', label='fitting')
        pylab.xlabel('Query ID')
        pylab.ylabel('Response Time (ms)')
        pylab.title('Response Times')

        ####################################################################

        fig, ax = pylab.subplots(2, 2, sharex=True, sharey=True) #2x2

        for i in range(2):
            for j in range(2):
                ax[i, j].set_title("Chip ({},{})".format(i,j))
                ax[i, j].bar(range(18), occ[i][j])

        ####################################################################

        chips = ('Chip (0,0)', 'Chip (0,1)', 'Chip (1,0)', 'Chip (1,1)')
        r = len(chips)

        colors ='rgbwmc'

        patch_handles = []

        fig = pylab.figure(figsize=(10,8))
        ax = fig.add_subplot(111)

        left = np.zeros(r,)
        row_counts = np.zeros(r,)

        def getID(x, y):
            if x is 0 and y is 0:
                return 0
            if x is 0 and y is 1:
                return 1
            if x is 1 and y is 0:
                return 2
            if x is 1 and y is 1:
                return 3

        print xyp_bytes
        for x, y, p in sorted(xyp_bytes):
            r = getID(x,y)
            bytes = xyp_bytes[x,y,p]

            patch_handles.append(
                ax.barh(r, bytes, align='center', left=left[r],
                        color=colors[int(row_counts[r]) % len(colors)],
                        edgecolor='black')
            )
            left[r] += bytes
            row_counts[r] += 1

            # we know there is only one patch but could enumerate if expanded
            patch = patch_handles[-1][0]
            bl = patch.get_xy()

            ax.text(0.5*patch.get_width() + bl[0],
                    0.5*patch.get_height() + bl[1],
                    bytes, ha='center',va='center')

        y_pos = np.arange(4)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(chips)
        ax.set_xlabel('Bytes')
        pylab.xlim([0, 120000000])

        pylab.show()
    """
    except Exception as e:
        outputText.delete('1.0', END)
        outputText.insert(INSERT, e)
    """

menu = MainMenu(root,queryScrolledText)

pingsFailed = 0
connected = True
pausePing = False

def ping():
    if not pausePing:
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