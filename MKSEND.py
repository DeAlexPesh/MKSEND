import os
import io
import PySimpleGUI as sg
import errno
import re
import requests
import socket
import sys
import time
import _thread
import threading

sg.ChangeLookAndFeel('LightGrey3')

threadFileSend = None


def log(s):
    window['_OUTPUT_'].print(s)
    return


def logClr(s=''):
    window['_OUTPUT_'].update(f'{s}\r\n')
    return


def getIp():
    ip = re.findall(r"(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$)", values['_IP_'])
    return ip[0] if ip else ''


def getCmnd():
    return values['_CMND_']


def getGcode():
    return values['_GCODE_']


def isPrinted():
    return values['_ISPRINTED_']


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
        # print(f'Command: {bCmnd}')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            # conn.settimeout(15.0)
            conn.connect((ip, port))
            conn.sendall(bCmnd)
            while True:
                line = ''
                data = b''
                while data != b'\n':
                    data = conn.recv(1)
                    line += data.decode('utf-8', 'ignore')
                line = line.replace("\n", "").replace("\r", "")
                # if line == 'ok':
                #     break
                result.append(line)
        result[0] = True
        print(f'Result: {result}')
    except socket.error as ex:
        e = ex.args[0]
        if e == errno.EAGAIN or e == errno.EWOULDBLOCK:
            result[0] = True
            print(f'Result: {result}')
        else:
            print(f'Exception: {ex}')
    except socket.timeout:
        result[0] = True
        print(f'Result: {result}')
    except Exception as ex:
        print(f'Exception: {ex}')
    finally:
        conn.close()
        conn = None
        return result


def getFilelist():
    ip = getIp()
    res = sendRawSocket('M20', ip)
    try:
        if res.pop(0):
            res.remove('Begin file list')
            res.remove('End file list')
            res.remove('ok')
    except:
        res = []
        pass
    return res


def updateFilelist():
    window.Element('_LISTBOX_').update(values=getFilelist())
    return


def getFilelistSelected():
    return values['_LISTBOX_']


def printFileByName(name):
    ip = getIp()
    if sendRawSocket(f'M23 {name}', ip)[0]:
        return sendRawSocket('M24', ip)[0]


def btnSendFile():
    ip = getIp()
    gcode = getGcode()
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
    ip = getIp()
    cmnd = getCmnd()
    logClr('-------')
    log(f'Выполнение: {cmnd}')
    res = sendRawSocket(cmnd, ip)
    if res.pop(0):
        for r in res:
            log(r)
    else:
        log('Не выполнено!')
    log('Выполнено.')
    return


layout = [
    [sg.Column([
        [sg.Frame(title=' IP адрес принтера ',
                  layout=[
                      [sg.InputText(key='_IP_',
                                    default_text='192.168.5.254',
                                    size=(30, 1),
                                    justification='center',
                                    background_color='#77ff77',
                                    change_submits=True,
                                    do_not_clear=True)]
                  ],
                  border_width=2,
                  pad=((5, 5), (0, 12)))
         ],
        [sg.Frame(title=' Загрузить файл ',
                  layout=[
                      [sg.InputText(key='_GCODE_',
                                    readonly=True, size=(30, 1),
                                    justification='right',
                                    background_color='#ffffff',
                                    change_submits=True,
                                    do_not_clear=True)],
                      [sg.ProgressBar(100, key='_PROGRESS_',
                                      orientation='h',
                                      size=(20, 20))],
                      [sg.FileBrowse(button_text='...',
                                     size=(3, 1),
                                     target='_GCODE_'),
                       sg.Submit(key='_SENDFILE_',
                                 button_text='Отправить',
                                 size=(10, 1)),
                       sg.Submit(key='_STOPSENDFILE_',
                                 button_text='Стоп',
                                 size=(10, 1)),
                       sg.Checkbox(key='_ISPRINTED_',
                                   text='печать')]
                  ],
                  border_width=2,
                  pad=((5, 5), (5, 10)))
         ],
        [sg.Frame(title=' Выполнить команду ',
                  layout=[
                      [sg.InputText(key='_CMND_',
                                    default_text='',
                                    size=(30, 1),
                                    justification='center',
                                    background_color='#ffffff',
                                    change_submits=True,
                                    do_not_clear=True)],
                      [sg.Submit(key='_SEND_',
                                 button_text='Выполнить',
                                 size=(15, 1))]
                  ],
                  border_width=2)
         ]
    ], pad=(0, 0)),
        sg.Column(layout=[
            [sg.Frame(title=' Загруженные файлы ',
                      layout=[
                          [sg.Listbox(key='_LISTBOX_', values=[], size=(
                              30, 10), background_color='#ffffff', select_mode=sg.LISTBOX_SELECT_MODE_EXTENDED)],
                          [sg.Submit(key='_TREEUPDATE_', button_text='Обновить', size=(8, 1)),
                           sg.Submit(key='_TREEDELETE_',
                                     button_text='Удалить', size=(7, 1)),
                           sg.Submit(key='_TREEPRINT_', button_text='Печать', size=(6, 1))]
                      ],
                      border_width=2,
                      pad=((8, 5), (0, 10)))
             ]
        ], pad=(0, 0))
    ],
    [sg.Multiline(key='_OUTPUT_', size=(66, 5),
                  disabled=True, pad=((5, 5), (10, 10)))]
]
window = sg.Window('MKSEND', layout)

sendFileThread = None

while True:
    event, values = window.read(timeout=500)

    if event in (None, 'Exit', 'Cancel'):
        break

    if event in ('_IP_'):
        window.Element(event).update(
            background_color=('#77ff77' if getIp() else '#ff7777'))

    if event in ('_SENDFILE_', '_SEND_'):
        if not getIp():
            logClr('Ошибка IP адреса!')
            continue

    if event in ('_SENDFILE_'):
        if not getGcode():
            logClr('Файл не выбран!')
        else:
            threadFileSend = StoppableThread(target=btnSendFile)
            print(threadFileSend)
            threadFileSend.start()

    if event in ('_STOPSENDFILE_'):
        if threadFileSend:
            threadFileSend.stop()
            print(threadFileSend)

    if event in ('_SEND_'):
        if not getCmnd():
            log('Команда отсутствует!')
        else:
            _thread.start_new_thread(btnSendCmnd, ())

    if event in ('_TREEUPDATE_'):
        _thread.start_new_thread(updateFilelist, ())

    if event in ('_TREEPRINT_'):
        ip = getIp()
        selected = getFilelistSelected()
        if len(selected) > 1:
            log('Отправить на печать можно только один элемент!')
        else:
            for s in selected:
                log('Печать...' if printFileByName(
                    s) else 'Ошибка запуска печати!')

    if event in ('_TREEDELETE_'):
        ip = getIp()
        selected = getFilelistSelected()
        for s in selected:
            if sendRawSocket(f'M30 0:/{s}', ip)[0]:
                log(f'{s} удален!')

    if event in ('_PRINTSTOP_'):
        sendRawSocket(f'M25', getIp())

window.close()
