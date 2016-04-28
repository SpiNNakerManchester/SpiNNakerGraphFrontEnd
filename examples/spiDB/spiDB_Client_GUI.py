import ScrolledText
import tkFileDialog
import tkMessageBox
from Tkinter import *
from time import *

import numpy as np
import pylab

from examples.spiDB.python.python_common.socket_connection \
    import SpiDBSocketConnection


class MainMenu(Frame):
    def __init__(self, parent, text_listener, top_parent):
        Frame.__init__(self, parent)
        self._top_parent = top_parent
        self.parent = parent
        self.text_listener = text_listener

        mbar = Menu(self.parent)
        self.parent.config(menu=mbar)

        self.file_menu = Menu(mbar)

        mbar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Open", command=self.on_open)
        self.file_menu.add_command(label="Quit", command=self.close)

        self.ping_menu = Menu(mbar)

        mbar.add_cascade(label="Ping", menu=self.ping_menu)

        self.pack(fill=BOTH, expand=1)

    @staticmethod
    def close():
        sys.exit(0)

    def on_open(self):
        file_spes = [('All files', '*'),
                    ('KV file', '*.kv'),
                    ('SQL file', '*.sql')]
        dlg = tkFileDialog.Open(self, filetypes = file_spes)
        fl = dlg.show()

        rf = self.read_file(fl)

        if not rf:
            return

        self.text_listener.delete('1.0', END)
        self.text_listener.insert(INSERT, rf)
        self._top_parent.highlight(None)

    @staticmethod
    def read_file(filename):
        if not filename:
            return None
        try:
            f = open(filename, "r")
            return f.read()
        except IOError:
            return None


class GUIBuilder(object):

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

    def __init__(self):

        self._conn = SpiDBSocketConnection(
            start_callback=self._turn_on_query, local_port=12387)
        self._history = dict()

        self._root = Tk()
        self._root.resizable(width=FALSE, height=FALSE)
        self._root.title("SpiDB")

        top_frame = Frame(self._root)
        top_frame.pack(side=TOP, padx=5, pady=5)

        bottom_frame = Frame(self._root)
        bottom_frame.pack(side=BOTTOM)

        left_frame = Frame(bottom_frame)
        left_frame.pack(side=LEFT, padx=20, pady=20)

        self._currentDbTypeStringVar = StringVar(top_frame)
        self._currentDbTypeStringVar.set('Key-Value')
        db_type_menu = OptionMenu(
            top_frame, self._currentDbTypeStringVar, 'Key-Value', 'SQL')

        db_type_menu.config(font=('calibri',(12)),width=16)
        db_type_menu['menu'].config(font=('calibri',(12)))

        db_type_menu.pack(side=LEFT)

        query_frame = Frame(left_frame)
        query_frame.pack(side=TOP, pady=(0, 10))

        history_frame = Frame(left_frame)
        history_frame.pack(side=BOTTOM)

        right_frame = Frame(bottom_frame)
        right_frame.pack(padx=20, pady=10)
        right_frame.pack(side=RIGHT)

        query_label = Label(query_frame, text="Query")
        query_label.pack(side=TOP)

        self._query_scrolled_text = ScrolledText.ScrolledText(
            master=query_frame,
            wrap='word',  # wrap text at full words only
            width=50,      # characters
            height=15,      # text lines
            bg='white')
        self._query_scrolled_text.pack(side=TOP)

        label = Label(history_frame, text="History")
        label.pack(side=TOP)

        self._history_list_box = Listbox(
            master=history_frame,
            width=40)
        self._history_list_box.pack()

        label = Label(right_frame, text="Output")
        label.pack(side=TOP)

        self._output_text = ScrolledText.ScrolledText(
            master=right_frame,
            wrap='word',  # wrap text at full words only
            width=80,      # characters
            height=30,      # text lines
            bg='white')

        self._menu = MainMenu(self._root, self._query_scrolled_text, self)

        self._history_list_box.bind('<<ListboxSelect>>', self.on_select)
        self._query_scrolled_text.bind('<Key>', self.highlight)

        self._pings_failed = 0
        self._connected = True
        self._pause_ping = False

        self._run_button = Button(
            query_frame, text="Run", state=DISABLED,
            fg="black", command=self.run_query)
        self._run_button.pack(side = RIGHT)

        clear_button = Button(
            query_frame, text="Clear", fg="black",
            command=self.clear_query)
        clear_button.pack(side=RIGHT)

        self._output_text.pack()

        self._root.mainloop()

    def highlight(self, e, scrolled_text='input'):

        if scrolled_text == 'input':
            scrolled_text = self._query_scrolled_text
            words = GUIBuilder.sql_keywords if \
                self._currentDbTypeStringVar.get() == "SQL" else \
                self.kv_keywords
        elif scrolled_text == 'output':
            scrolled_text = self._output_text
            words = {'OK': ('', 'green'),
                     'FAIL': ('', 'red')}
        else:
            return

        for k, v in words.iteritems():
            start = '1.0'
            while start:
                start = scrolled_text.search(k, start, END)
                if start:
                    end = scrolled_text.index('%s+%dc' % (start, len(k)))
                    scrolled_text.tag_add(k, start, end)
                    scrolled_text.tag_config(k,
                                             background=v[0],
                                             foreground=v[1])
                    start = end

    @staticmethod
    def empty_query_popup():
        tkMessageBox.showinfo("Query Error", "Cannot run empty query")

    def _turn_on_query(self):
        self._run_button.configure(state=NORMAL)

    def on_select(self, evt):
        w = evt.widget
        if not w.curselection():
            return
        index = int(w.curselection()[0])
        value = w.get(index)

        self._query_scrolled_text.delete('1.0', END)
        self._query_scrolled_text.insert(INSERT, self._history[value][0])

        self._output_text.delete('1.0', END)
        self._output_text.insert(INSERT, self._history[value][1])

    def clear_query(self):
        self._query_scrolled_text.delete('1.0', END)

    def ping(self):
        if not self._pause_ping:
            p = self._conn.send_ping()
            self._menu.ping_menu.delete(12)
            if p is -1:
                self._menu.ping_menu.insert_command(
                    index=0, label="PING FAILED", command=None)
                self._pings_failed += 1
                if self._connected and self._pings_failed is 2:
                    self._connected = False
                    tkMessageBox.showinfo(
                        "Ping failed", "Cannot connect to board")
            else:
                self._connected = True
                self._pings_failed = 0
                self._menu.ping_menu.insert_command(
                    index=0, label="PING {:.3f}ms".format(p), command=None)
        self._root.after(1000, self.ping)

    def run_query(self):
        self._pause_ping = True
        truncate_index = 30
        q_text = self._query_scrolled_text.get('1.0', 'end')

        if q_text.isspace():
            self.empty_query_popup()
            return

        self._output_text.delete('1.0', END)
        self._output_text.insert(INSERT, "Running...")

        error = True
        results = []
        downloads = list()
        uploads = list()

        #ms
        total_download_time_sec = 0
        total_upload_time_sec = 0
        total_time_sec = 0

        packets_sent = 0
        packets_received = 0

        try:
            if self._currentDbTypeStringVar.get() == 'SQL':
                for stage in q_text.split('.'):
                    statements = [s.strip() for s in stage.split(';')]

                    r = self._conn.execute(statements, 'SQL')

                    results.extend(r["results"])
                    downloads.extend(r["download"])
                    uploads.extend(r["upload"])
                    total_upload_time_sec += r["uploadTimeSec"]
                    total_download_time_sec += r["downloadTimeSec"]
                    packets_sent += r["packetsSent"]
                    packets_received += r["packetsReceived"]
                    total_time_sec += r["totalTimeSec"]
            else:
                for stage in q_text.split('.'):
                    r = self._conn.execute(stage.split('\n'), 'Key-Value')

                    results.extend(r["results"])
                    downloads.extend(r["download"])
                    uploads.extend(r["upload"])
                    total_upload_time_sec += r["uploadTimeSec"]
                    total_download_time_sec += r["downloadTimeSec"]
                    packets_sent += r["packetsSent"]
                    packets_received += r["packetsReceived"]
                    total_time_sec += r["totalTimeSec"]
        except Exception as e:
            self._output_text.delete('1.0', END)
            tkMessageBox.showinfo("Query failed", e)
            return

        self._pause_ping = False
        """except Exception as e:
            outputText.delete('1.0', END)
            outputText.insert(INSERT, e)
            return
        """

        xyp_occurences = dict()
        xyp_bytes = dict()
        response_times = list()
        occ = [[[0 for p in range(18)] for y in range(2)] for x in range(2)]

        total_response_times_added_up = 0
        for r in results:
            if r is not None:
                for resp in r.responses:
                    if resp.__xyp__() in xyp_occurences:
                        xyp_occurences[resp.__xyp__()] += 1
                        if resp.cmd == "PUT":
                            xyp_bytes[resp.__xyp__()] += resp.data
                    else:
                        xyp_occurences[resp.__xyp__()] = 1
                        if resp.cmd == "PUT":
                            xyp_bytes[resp.__xyp__()] = resp.data
                    response_times.append(resp.response_time)
                    total_response_times_added_up += resp.response_time

        for xyp, o in xyp_occurences.iteritems():
            (x, y, p) = xyp
            occ[x][y][p] = o

        bytes_snt = sum([x[1] for x in uploads])
        bytes_rcv = sum([x[1] for x in downloads])

        unreplied = packets_sent-packets_received if \
            packets_received < packets_sent else 0

        s = "Statistics:\n\n" \
            "  performance:             {:,.1f} op/sec\n\n" \
            "  total upload time:       {:.4f} sec\n"\
            "  total download time:     {:.4f} sec\n\n"\
            "  average latency:         {:.4f} ms\n\n"\
            "  packets sent:            {:>8}       {:.3f} Kbytes\n"\
            "  packets received:        {:>8}       {:.3f} Kbytes\n"\
            "  packets unreplied/lost:  {:>8}       {:.2f}%\n\n" \
            "########################################################\n\n"\
            .format(0 if total_time_sec is 0 else
                                packets_received/total_upload_time_sec,
                    total_upload_time_sec,
                    total_download_time_sec,
                    0 if packets_received is 0 else
                                total_response_times_added_up/packets_received,
                    "{:,}".format(packets_sent), bytes_snt/1000.0,
                    "{:,}".format(packets_received), bytes_rcv/1000.0,
                    "{:,}".format(unreplied),
                    0 if packets_sent is 0 else (100.0*unreplied)/packets_sent)

        for r in results:
            if r is None:
                s += "No response\n"
            else:
                error = False
                s += "{}\n".format(str(r))

        self._output_text.delete('1.0', END)
        self._output_text.insert(INSERT, s)
        self.highlight(None, scrolled_text='output')

        query_result_tuple = (q_text, s)

        t = strftime("%H:%M:%S", gmtime())
        q_text = (q_text[:truncate_index] + '...')\
            if len(q_text) > truncate_index else q_text
        q_text = "{}  {}".format(t,q_text)
        self._history_list_box.insert(0,q_text)
        self._history[q_text] = query_result_tuple

        if not error and len(response_times) > 2:
            #########################################################

            x_up_load = [x[0] for x in uploads]
            y_up_load = [x[1] for x in uploads]

            x_download = [x[0] for x in downloads]
            y_download = [x[1] for x in downloads]

            pylab.figure()
            fig = pylab.gcf()
            fig.canvas.set_window_title('Network Traffic')
            pylab.plot(
                x_up_load, np.poly1d(np.polyfit(x_up_load, y_up_load, 5))
                (x_up_load), 'b', label='Upload')
            pylab.plot(
                x_download, np.poly1d(np.polyfit(x_download, y_download, 5))
                (x_download), 'g', label='Download')
            pylab.legend(loc='upper left')
            pylab.xlabel('Query ID')
            pylab.ylabel('Bytes')
            pylab.title('Network Traffic')

            ####################################################################
            pylab.figure()
            fig = pylab.gcf()
            fig.canvas.set_window_title('Response Times')

            x = range(len(response_times))
            y = response_times
            pylab.ylim([0, max(1, max(response_times)+0.1)])
            pylab.plot(x, y, 'bo', label='sample')

            pylab.plot(x, np.poly1d(np.polyfit(x, y, 5))(x), 'r',
                       label='fitting')
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

            if xyp_bytes:
                chips = ('Chip (0,0)', 'Chip (0,1)', 'Chip (1,0)', 'Chip (1,1)')
                r = len(chips)

                colors = 'rgbwmc'

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

                # print xyp_bytes
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

                    # we know there is only one patch but could
                    #  enumerate if expanded
                    patch = patch_handles[-1][0]
                    bl = patch.get_xy()

                    ax.text(0.5*patch.get_width() + bl[0],
                            0.5*patch.get_height() + bl[1],
                            bytes, ha='center',va='center')

                y_pos = np.arange(4)
                ax.set_yticks(y_pos)
                ax.set_yticklabels(chips)
                ax.set_xlabel('Bytes')

            pylab.show()

if __name__ == "__main__":
    GUIBuilder()
