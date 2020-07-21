import os
import PySimpleGUI as sg
import re
import requests
import socket
import sys
import time

sg.ChangeLookAndFeel('LightGrey3')


def logCls():
    window['_OUTPUT_'].update('')
    return


def log(s):
    window['_OUTPUT_'].print(s)
    return


def getIp():
    ip = re.findall(r"(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$)", values['_IP_'])
    return ip[0] if ip else ''


def getCmnd():
    return values['_CMND_']


def getGcode():
    return values['_GCODE_']


def isPrinted():
    return values['_PRINT_GCODE_']


def sendRawSocket(cmnd, ip, port=8080):
    try:
        result = [False]
        bCmnd = str.encode(cmnd + '\r\n')
        print(bCmnd)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            conn.connect((ip, port))
            conn.sendall(bCmnd)
            reply = ''
            while reply != 'ok':
                reply = ''
                data = b''
                while data != b'\n':
                    data = conn.recv(1)
                    reply = reply + str(data, 'utf-8')
                reply = reply.replace("\n", "").replace("\r", "")
                result.append(reply)
        result[0] = True
        print(result)
    except Exception as ex:
        print(f'Exception: {ex}')
    finally:
        conn.close()
        conn = None
        return result


def sendFile(file, fileName, ip, port=80):
    try:
        with open(file, 'rb') as f:
            data = f.read()
        url = f'http://{ip}:{port}/upload?X-Filename={fileName}'
        res = requests.post(url=url,
                            data=data,
                            headers={'Content-Type': 'application/octet-stream'})
        time.sleep(3)
        return False if res.status_code != 200 else True
    except Exception as ex:
        print(f'Exception: {ex}')
        return False


layout = [
    [sg.Column(layout=[
        [sg.Frame(title=' IP адрес принтера ',
                  layout=[
                      [sg.InputText(key='_IP_', default_text='192.168.5.254', size=(33, 1),
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
                                 key='_SENDFILE_', size=(10, 1)),
                       sg.Checkbox(text='печать', key='_PRINT_GCODE_')]
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
                                     key='_TREEUPDATE_', size=(10, 1)),
                           sg.Submit(button_text='Печать',
                                     key='_TREEPRINT_', size=(10, 1)),
                           sg.Submit(button_text='Удалить',
                                     key='_TREEDELETE_', size=(10, 1)),
                           sg.Submit(button_text='Стоп',
                                     key='_PRINTSTOP_', size=(10, 1))],
                          [sg.Listbox(values=[], size=(21, 10), enable_events=True,
                                      bind_return_key=True, select_mode='single', key='_LISTBOX_')]
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
        if getIp():
            window.Element(event).update(background_color='white')
        else:
            window.Element(event).update(background_color='#ff5555')

    if event in ('_SENDFILE_', '_SEND_'):
        if not getIp():
            log('Выберите IP!')
            continue

    if event in ('_SENDFILE_'):
        gcode = getGcode()
        if not gcode:
            log('Выберите файл GCODE!')
        else:
            log('Загрузка файла на принтер...')
            ip = getIp()
            fileName = os.path.basename(gcode)
            if sendFile(gcode, fileName, ip):
                if isPrinted():
                    log('Запуск печати...')
                    if sendRawSocket(f'M23 {fileName}', ip)[0]:
                        if sendRawSocket('M24', ip)[0]:
                            log('Печать...')
                        else:
                            log('Ошибка запуска печати!')
                    else:
                        log('Ошибка выбора файла!')
                else:
                    log('Файл загружен!')
            else:
                log('Ошибка отправки файла!')

    if event in ('_SEND_'):
        cmnd = getCmnd()
        if not cmnd:
            log('Введите команду!')
        else:
            log('Отправка комманды...')
            ip = getIp()
            res = sendRawSocket(cmnd, ip)
            if res.pop(0):
                logCls()
                for s in res:
                    log(s)
            else:
                log('Ошибка выполнения комманды!')

    if event in ('_TREEUPDATE_'):
        ip = getIp()
        res = sendRawSocket('M20', ip)
        if res.pop(0):
            res.remove('Begin file list')
            res.remove('End file list')
            res.remove('ok')
            window.Element('_LISTBOX_').update(values=res)

    if event in ('_TREEPRINT_'):
        ip = getIp()
        selected = values['_LISTBOX_']
        if len(selected) > 1:
            log('Отправить на печать можно только один элемент!')
        else:
            for s in selected:
                if sendRawSocket(f'M23 {s}', ip)[0]:
                    if sendRawSocket('M24', ip)[0]:
                        log('Печать...')

    if event in ('_TREEDELETE_'):
        ip = getIp()
        selected = values['_LISTBOX_']
        for s in selected:
            if sendRawSocket(f'M30 /{s}', ip)[0]:
                log(f'{s} удален!')

    if event in ('_PRINTSTOP_'):
        ip = getIp()
        sendRawSocket(f'M25', ip)
window.close()
