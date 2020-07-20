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
    [sg.Text('IP:', size=(7, 1), justification='right'),
     sg.InputText(key='_IP_', size=(25, 1), background_color='white', justification='center',
                  change_submits=True, do_not_clear=True, default_text=ip)],
    [sg.Text('CMND:', size=(7, 1), justification='right'),
     sg.InputText(key='_CMND_', size=(25, 1), justification='center',
                  change_submits=True, do_not_clear=True),
     sg.Submit('Отправить', key='_SEND_', size=(15, 1))],
    [sg.Text('GCODE:', size=(7, 1), justification='right'),
     sg.InputText(key='_GCODE_', size=(25, 1), change_submits=True,
                  do_not_clear=True, readonly=True),
     sg.FileBrowse('...', size=(3, 1)),
     sg.Submit('Печать', key='_PRINT_', size=(10, 1))],
    [sg.Text('ECHO:', size=(7, 10), justification='right'),
     sg.Multiline(key='_OUTPUT_', size=(42, 10), disabled=True)],
    [sg.Text('', size=(7, 1), justification='right'), sg.ProgressBar(
        100, key='_PROGRESS_', size=(29, 20), orientation='h')],
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

    if event in ('_PRINT_', '_SEND_'):
        if not ip:
            echo('Выберите IP!', True)
            continue

    if event in ('_PRINT_'):
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
