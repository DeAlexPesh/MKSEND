import PySimpleGUI as sg
import re
import socket
import sys
import os

sg.ChangeLookAndFeel('LightGreen')

ip = '192.168.5.254'
httpPort = 80
tcpPort = 8080
gcode = ''
cmnd = ''


def rawSocketSend():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            conn.connect((ip, tcpPort))
            conn.sendall(cmnd)
            while 1:
                reply = ''
                data = ''
                while data != b'\n':
                    data = conn.recv(1)
                    reply = reply + str(data, 'utf-8')

                reply = reply.replace("\n", "").replace("\r", "")
                print('Received:', repr(reply))

    except socket.error as exc:
        print("Caught exception socket.error : %s" + exc)
    finally:
        conn.close()
    return


layout = [
    [sg.Text('IP:', size=(7, 1), justification='right'), sg.In(key='_IP_', size=(
        15, 1), change_submits=True, do_not_clear=True, default_text=ip)],
    [sg.Text('GCODE:', size=(7, 1), justification='right'), sg.In(key='_GCODE_', size=(
        25, 1), change_submits=True, do_not_clear=True, readonly=True), sg.FileBrowse('Обзор', size=(10, 1)), sg.Submit('Печать', key='_PRINT_', size=(10, 1))],
    [sg.Text('CMND:', size=(7, 1), justification='right'), sg.In(key='_CMND_', size=(
        25, 1), change_submits=True, do_not_clear=True), sg.Submit('Отправить', key='_SEND_', size=(10, 1))]
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
            print('ip')
        else:
            ip = ''

        # window[event].update(ip_entered)

    if event in ('_GCODE_'):
        gcode = values[event]
        print(gcode)

    if event in ('_CMND_'):
        cmnd = str.encode(values[event] + '\r\n')
        print(cmnd)

    if event in ('_PRINT_'):
        if not ip:
            print('Введите IP!')
            continue

        if not gcode:
            print('Выберите GCODE!')
            continue
        else:
            file = re.findall('.+:\/.+\.+.', gcode)
            if not file and file is not None:
                print('Ошибка чтения файла!')
            else:
                print('Print')

    if event in ('_SEND_'):
        if not ip:
            print('Введите IP!')
            continue

        if not cmnd:
            print('Введите команду!')
            continue
        else:
            rawSocketSend()

window.close()
