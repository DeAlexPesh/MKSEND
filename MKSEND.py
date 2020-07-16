import PySimpleGUI as sg
import re

sg.ChangeLookAndFeel('LightGreen')

ip = '192.168.5.254'
gcode = ''
cmnd = ''

layout = [
    [sg.Text('IP:', size=(7, 1), justification='right'), sg.In(key='_IP_', size=(
        15, 1), change_submits=True, do_not_clear=True, default_text=ip)],
    [sg.Text('GCODE:', size=(7, 1), justification='right'), sg.In(key='_GCODE_', size=(
        25, 1), change_submits=True, do_not_clear=True, readonly=True), sg.FileBrowse('Обзор', size=(10, 1)), sg.Submit('Печать', size=(10, 1))],
    [sg.Text('CMND:', size=(7, 1), justification='right'), sg.In(key='_CMND_', size=(
        25, 1), change_submits=True, do_not_clear=True), sg.Submit('Отправить', size=(10, 1))]
]
window = sg.Window('MKSEND', layout)

while True:
    event, values = window.read()

    if event in (None, 'Exit', 'Cancel'):
        break
    if event in ('_IP_'):
        ip_entered = values[event]
        print(re.findall(
            r"(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$)", ip_entered))

        # window[event].update(ip_entered)

    if event == 'Печать':
        if not values[0]:
            print('Введите IP !')
        if values[1]:
            file = re.findall('.+:\/.+\.+.', values[1])
            if not file and file is not None:
                print('Error: File path not valid.')
            else:
                print('Send')
        else:
            print('Please FILE')

    if event == 'Отправить':
        if values[2]:
            print('Send')
        else:
            print('Please CMND')

window.close()
