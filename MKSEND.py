import os
import io
import PySimpleGUI as sg
import re
import requests
import socket
import sys
import time
import _thread
import threading
import queue
import platform
import tkinter as tk
import tkinter.ttk as ttk

sg.ChangeLookAndFeel('LightGrey3')

OS_NAME = platform.system()

threadFileSend = None


def log(s):
    window['_OUTPUT_'].print(s)
    return


def logClr(s=''):
    window['_OUTPUT_'].update(f'{s}\r\n')
    return

def setProgress(size, progress):
    window.Element('_PROGRESS_').update_bar(float(progress)/float(size)*100)


def setProgressErr():
    window.Element('_PROGRESS_').update(bar_color=('#ff7777'))


class StoppableThread(threading.Thread):
    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class BufferReader(io.BytesIO):
    def __init__(self, buf=b'', callback=None, cb_args=(), cb_kwargs={}):
        self._callback = callback
        self._cb_args = cb_args
        self._cb_kwargs = cb_kwargs
        self._progress = 0
        self._len = len(buf)
        io.BytesIO.__init__(self, buf)

    def __len__(self):
        return self._len

    def read(self, n=-1):
        chunk = io.BytesIO.read(self, n)
        self._progress += int(len(chunk))
        self._cb_kwargs.update({
            'size': self._len,
            'progress': self._progress
        })
        if self._callback:
            try:
                self._callback(*self._cb_args, **self._cb_kwargs)
            except Exception as ex:
                raise ex
        return chunk


def sendFile(file, fileName, ip, port=80):
    result = False
    try:
        with open(file, 'rb') as f:
            body = f.read()
        data = BufferReader(body, setProgress)
        url = f'http://{ip}:{port}/upload?X-Filename={fileName}'
        res = requests.post(url=url,
                            data=data,
                            headers={'Content-Type': 'application/octet-stream'})
        scode = res.status_code
        if scode != 200:
            raise Exception(scode)
        else:
            time.sleep(3)
            result = True
    except Exception as ex:
        print(f'Exception: {ex}')
        pass
    finally:
        return result


def sendRawSocket(cmnd, ip, port=8080):
    result = [False]
    try:
        bCmnd = f'{cmnd}\r\n'.encode('utf-8', 'ignore')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            conn.settimeout(10.0)
            conn.connect((ip, port))
            conn.sendall(bCmnd)
            run = True
            while run:
                line = ''
                data = b''
                while data != b'\n':
                    data = conn.recv(1)
                    print(data)
                    if data:
                        line += data.decode('utf-8', 'ignore')
                line = line.replace("\n", "").replace("\r", "")
                if line:
                    result.append(line)
        result[0] = True
        print(f'Result: {result}')
    except socket.timeout:
        result[0] = True
        print(f'Result: {result}')
    except Exception as ex:
        print(f'Exception: {ex}')
    finally:
        if OS_NAME == 'Linux':
            conn.shutdown(socket.SHUT_RDWR)
        conn.close()
        return result



def printFileByName(name):
    ip = gui.getIp()
    if sendRawSocket(f'M23 {name}', ip)[0]:
        return sendRawSocket('M24', ip)[0]


def btnSendFile():
    ip = gui.getIp()
    gcode = gui.getFile()
    fileName = os.path.basename(gcode)
    if sendFile(gcode, fileName, ip):
        log('Файл загружен.')
        if isPrinted():
            log('Запуск печати...')
            log('Печать.' if printFileByName(fileName)
                else 'Ошибка запуска печати!')
    else:
        log('Ошибка загрузки файла!')
    return


def btnSendCmnd():
    ip = gui.getIp()
    cmnd = gui.getGcode()
    logClr('-------')
    log(f'Выполнение: {cmnd}')
    res = sendRawSocket(cmnd, ip)
    if res.pop(0):
        for r in res:
            log(r)
        log('Выполнено.')
    else:
        log('Не выполнено!')
    return


class MKSEND:
    def __init__(self, master):
        self.master = master
        master.title("MKSEND")

        ipFrame = tk.LabelFrame(master, text = " IP адрес принтера ")
        
        svIpInput = tk.StringVar()
        svIpInput.trace("w", lambda name, index, mode, sv=svIpInput: self.__ipCallback(svIpInput))
        self.__ipInput = tk.Entry(ipFrame, textvariable = svIpInput, bd = 0, bg = "#77ff77", justify = tk.CENTER)
        self.__ipInput.insert(tk.END, "192.168.5.254")
        self.__ipInput.pack(fill = tk.BOTH, ipady = 2, padx = 4, pady = 4)

        ipFrame.grid(column = 1, columnspan = 1, padx = 4, pady = (2, 4), row = 1, rowspan = 1, sticky="NWE")


        sendFileFrame = tk.LabelFrame(master, text = " Загрузить файл ")

        self.__sendFileLabel = tk.Label(sendFileFrame, text = "", bg = "#ffffff")
        self.__sendFileLabel.grid(column = 1, columnspan = 5, ipadx = 2, ipady = 2, padx = (4, 0), pady = (2, 0), row = 1, rowspan = 1, sticky="NWES")

        sendFileBtnOpen = tk.Button(sendFileFrame, text = "...", command = self.__fileBrowse)
        sendFileBtnOpen.grid(column = 6, columnspan = 1, ipadx = 2, padx = (0, 4), pady = (2, 0), row = 1, rowspan = 1, sticky="NWE")

        self.__sendFileBtn = tk.Button(sendFileFrame, text = "Отправить", command = self.__sendFile)
        self.__sendFileBtn.grid(column = 1, columnspan = 1, ipadx = 2, padx = (4, 0), pady = (4, 0), row = 2, rowspan = 1, sticky="NWE")

        self.__isPrinted = tk.IntVar()
        self.__isPrinted.set(1)
        self.__sendFileIsPrinted = tk.Checkbutton(sendFileFrame, text = "Напечатать", variable = self.__isPrinted, onvalue = 1, offvalue = 0)
        self.__sendFileIsPrinted.grid(column = 2, columnspan = 1, ipadx = 2, padx = 4, pady = (4, 0), row = 2, rowspan = 1, sticky="NW")

        self.__sendFilePB = ttk.Progressbar(sendFileFrame, orient = tk.HORIZONTAL, length = 100)
        #self.__sendFilePB.pack()

        self.__sendFileCancelBtn = tk.Button(sendFileFrame, text = "Отмена", command = self.__cancelSendFile)
        #self.__sendFileCancelBtn.pack()

        sendFileFrame.grid(column = 1, columnspan = 1, padx = 4, pady = 2, row = 2, rowspan = 1, sticky="NWE")


        gcodeFrame = tk.LabelFrame(master, text = " Выполнить команду ")

        self.gcodeInput = tk.Entry(gcodeFrame, bd = 0, justify = tk.CENTER)
        self.gcodeInput.pack(fill = tk.BOTH, ipady = 2, padx = 4, pady = (2, 0))

        self.gcodeBtn = tk.Button(gcodeFrame, text = "Выполнить", command = _thread.start_new_thread(self.__sendGcode, ()))
        self.gcodeBtn.pack(fill = tk.BOTH, padx = 4, pady = 4)

        gcodeFrame.grid(column = 1, columnspan = 1, padx = 4, pady = 2, row = 3, rowspan = 1, sticky="NWE")


        fileFrame = tk.LabelFrame(master, text = " Загруженные файлы ")        

        filePaneListbox = tk.Frame(fileFrame, bg = "#ffffff")
        filePaneListbox.pack(fill = tk.BOTH, padx = 4, pady = (2, 0))
        self.fileListbox = tk.Listbox(filePaneListbox, bd = 0, bg = filePaneListbox.cget("bg"), selectmode = tk.EXTENDED, highlightthickness = 0, borderwidth = 0)
        fileScrollbar = tk.Scrollbar(filePaneListbox, bg = filePaneListbox.cget("bg"))
        fileScrollbar.config(command = self.fileListbox.yview)
        self.fileListbox.pack(side = tk.LEFT, padx = 2, pady = 2, fill = tk.BOTH)
        fileScrollbar.pack(side = tk.RIGHT, fill = tk.Y)
        self.fileListbox.config(yscrollcommand = fileScrollbar.set)

        self.fileUpdateBtn = tk.Button(fileFrame, text = "Удалить", command = self.__removeFile)
        self.fileUpdateBtn.pack(side = tk.BOTTOM, fill = tk.BOTH, padx = 4, pady = (0, 4))

        self.filePrintBtn = tk.Button(fileFrame, text = "Печать", command = self.__printFile)
        self.filePrintBtn.pack(side = tk.BOTTOM, fill = tk.BOTH, padx = 4, pady = 0)  

        self.fileUpdateBtn = tk.Button(fileFrame, text = "Обновить", command = _thread.start_new_thread(self.__updateFileList, ()))
        self.fileUpdateBtn.pack(side = tk.BOTTOM, fill = tk.BOTH, padx = 4, pady = (2, 0))

        fileFrame.grid(column = 2, columnspan = 1, padx = (0, 4), pady = 2, row = 1, rowspan = 4, sticky="NWES")


        self.closeBtn = tk.Button(master, text = "Close", command = master.quit)
        #self.closeBtn.pack()

    def getIp(self):
        ip = re.findall(r"(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$)", self.__ipInput.get())
        return ip[0] if ip else ''

    def __ipCallback(self, sv):
        self.__ipInput.configure(bg=('#77ff77' if self.getIp() else '#ff7777'))

    def getFile(self):
       return self.__sendFileLabel.cget()

    def __fileBrowse(self): 
      fileName = tk.filedialog.askopenfilename(initialdir = "/", title = "Выбор файла", filetypes = (("GCODE", "*.gcode*"), ("Все", "*.*"))) 
      self.__sendFileLabel.configure(text = fileName)

    def __sendFile(self):
        return

    def __cancelSendFile(self):
        return

    def getGcode(self):
        return self.gcodeInput.get()

    def __sendGcode(self):
        return

    def __getSelectedFile(self):
       ids = self.fileListbox.curselection()
       sels = []
       for i in ids:
           sels.append(self.fileListbox.get(i))
       return sels

    def __updateFileList(self):
       ip = self.getIp()
       gList = [True,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #sendRawSocket('M20', ip)
       if gList.pop(0):
           try:
             elBgn = 1 #gList.index('Begin file list') + 1
             elEnd = 15 #gList.index('End file list')
             while elBgn != elEnd:
                self.fileListbox.insert(tk.END, gList[elBgn])
                elBgn += 1
           except:
               pass
    
    def __printFile(self):
        print(self.__getSelectedFile())
        return

    def __removeFile(self):
        return

root = tk.Tk()
gui = MKSEND(root)
root.mainloop()
