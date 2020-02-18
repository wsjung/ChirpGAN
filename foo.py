import PySimpleGUI as sg

event, values = sg.Window('Select Audio Files').Layout([[sg.Input(key='_FILES_'), sg.FilesBrowse()], [sg.OK(), sg.Cancel()]]).Read()
print(values['_FILES_'].split(';'))
