import PySimpleGUI as sg

#sg.theme('DarkAmber')	# color

# basic window

main_layout = [
	[sg.Text('Main Menu')],
	[sg.Button('Load Data')],
	[sg.Exit()]
]

load_data_layout = [
	[sg.Text('Bird vocalization files to load: ')],
	[sg.Input(key='_FILES_'), sg.FilesBrowse()],
	[sg.OK(), sg.Cancel()]
]


load_data_popup = sg.Window('Select audio file(s)').Layout(load_data_layout)
main_window = sg.Window('Main Menu').Layout(main_layout)

while True:
	event, values = main_window.read()
	print('event: %s\nvalues: %s' % (event, values))
	if event in ('Load Data'):
		while True:
			ld_event, ld_values = load_data_popup.read()
			#print('ld_event: %s\nld_values: %s' % (ld_event, ld_values))
			if ld_event in ('OK'):
				print('### SELECTED FILES ###')
				print(ld_values['_FILES_'].split(';'))
			if ld_event in (None, 'Cancel'):
				load_data_popup.close()
				break
	if event in (None, 'Exit'):
		break

main_window.close()
