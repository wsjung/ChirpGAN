import PySimpleGUI as sg

#sg.theme('DarkAmber')	# color

# basic window

main_layout = [
	[sg.Text('Main Menu')],
	[sg.Button('Load Data')],
	[sg.Exit()]
]

load_data_layout = [
	[sg.Text('Bird vocalization files to load...')],
	[sg.In(), sg.FileBrowse()],
	[sg.Open(), sg.Cancel()]
]

load_data_popup = sg.Window('Load Data').Layout(load_data_layout)
main_window = sg.Window('Main Menu').Layout(main_layout)

while True:
	event, values = main_window.read()
	print(event, values)
	if event in ('Load Data'):
	#	load_data_popup.read()
		fnames = sg.popup_get_file('Bird vocalization files to load')
		print(fnames)
	if event in (None, 'Exit'):
		break

main_window.close()
