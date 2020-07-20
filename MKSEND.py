import PySimpleGUI as sg
import re
import socket
import sys
import os
import requests
import time

sg.ChangeLookAndFeel('LightGrey3')

ip = '192.168.5.254'
httpPort = 80
sockPort = 8080
inGcode = ''
inCmnd = ''
upItems = ['a','b','c','d']

def showPopup(s):
    sg.popup(s, no_titlebar=True, keep_on_top=True)


def echo(s, isNew=False):
    if isNew:
        window['_OUTPUT_'].update(s)
    else:
        window['_OUTPUT_'].print(s)
    return


def sendRawSocket(i, isLog=False):
    try:
        cmnd = str.encode(i + '\r\n')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            conn.connect((ip, sockPort))
            conn.sendall(cmnd)
            reply = ''
            while reply != 'ok':
                reply = ''
                data = b''
                while data != b'\n':
                    data = conn.recv(1)
                    reply = reply + str(data, 'utf-8')
                reply = reply.replace("\n", "").replace("\r", "")
                if isLog:
                    echo(reply)
        return True
    except Exception as ex:
        echo(f'Exception: {ex}')
        return False
    finally:
        conn.close()
        conn = None


def sendFile(fileUrl):
    try:
        with open(fileUrl, 'rb') as f:
            fileData = f.read()
        fileName = os.path.basename(fileUrl)
        url = f'http://{ip}/upload?X-Filename={fileName}'
        res = requests.post(url=url,
                            data=fileData,
                            headers={'Content-Type': 'application/octet-stream'})
        return False if res.status_code != 200 else True
    except Exception as ex:
        echo(f'Exception: {ex}')
        return False


layout = [
    [sg.Column(layout=[
        [sg.Frame(title=' IP адрес принтера ',
                  layout=[
                      [sg.InputText(key='_IP_', default_text=ip, size=(33, 1),
                                    justification='center', background_color='white',
                                    change_submits=True, do_not_clear=True)]
                  ],
                  border_width=1)
         ],
        [sg.Frame(title=' Отправить файл ',
                  layout=[
                      [sg.InputText(key='_GCODE_', size=(33, 1), change_submits=True,
                                    do_not_clear=True, readonly=True)],
                      [sg.FileBrowse(button_text='...', size=(3, 1), target='_GCODE_'),
                       sg.Submit(button_text='Отправить',
                                 key='_SEND_FILE_', size=(10, 1)),
                       sg.Checkbox(text='печать', key='_PRINT_FILE_')]
                  ],
                  border_width=1)
         ],
        [sg.Frame(title=' Отправить команду ',
                  layout=[
                      [sg.InputText(key='_CMND_', default_text='', size=(33, 1),
                                    justification='center', background_color='white',
                                    change_submits=True, do_not_clear=True)],
                      [sg.Submit(button_text='Отправить',
                                 key='_SEND_', size=(15, 1))]
                  ],
                  border_width=1)
         ]
    ], pad=(0, 0)),
        sg.Column(layout=[
            [sg.Frame(title=' Загруженные файлы ',
                      layout=[
                          [sg.Submit(button_text='Обновить',
                                     key='_TREE_UPDATE_', size=(20, 1))],
                          [sg.Listbox(values=upItems, size=(21,10), enable_events=True, bind_return_key=True, select_mode='single', key='_LISTBOX_')]
                      ],
                      border_width=0)
             ]
        ], pad=(0, 0))
    ],
    [sg.Multiline(key='_OUTPUT_', disabled=True)]
]
window = sg.Window('MKSEND', layout)

while True:
    event, values = window.read()

    if event in (None, 'Exit', 'Cancel'):
        break

    if event in ('_IP_'):
        ipEntered = values[event]
        isIp = re.findall(
            r"(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$)", ipEntered)
        if isIp:
            ip = ipEntered
            window.Element(event).update(background_color='white')
        else:
            ip = ''
            window.Element(event).update(background_color='#ff5555')

    if event in ('_GCODE_'):
        inGcode = values[event]

    if event in ('_CMND_'):
        inCmnd = values[event]

    if event in ('_SEND_FILE_', '_SEND_'):
        if not ip:
            showPopup('Выберите IP!')
            continue

    if event in ('_SEND_FILE_'):
        if not inGcode:
            echo('Выберите файл GCODE!', True)
        else:
            echo('', True)
            echo('Отправка файла на принтер...', True)
            if sendFile(inGcode):
                time.sleep(5)
                echo('Запуск печати...')
                fileName = os.path.basename(inGcode)
                if sendRawSocket(f'M23 {fileName}'):
                    if sendRawSocket('M24'):
                        echo(f'Печать...')
                    else:
                        echo('Ошибка запуска печати!')
                else:
                    echo('Ошибка выбора файла!')
            else:
                echo('Ошибка отправки файла!')

    if event in ('_SEND_'):
        if not inCmnd:
            echo('Введите команду!', True)
        else:
            echo('', True)
            sendRawSocket(inCmnd, True)

window.close()
