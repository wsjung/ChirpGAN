import PySimpleGUI as sg
import os
import tempfile
import gzip
import shutil
import glob


from scalogram.pipeline import WavPipeline



#sg.theme('DarkAmber')	# color

# basic window

main_layout = [
[sg.Text('Main Menu')],
[sg.Button('Load Data')],
[sg.Exit()]
]

#TODO: allow ability to select and load multiple files
load_data_layout = [
[sg.Text('Folder of bird vocalization files to load: ')],
[sg.Input(key='_FILES_'), sg.FolderBrowse()], 
[sg.OK(), sg.Cancel()]
]


load_data_popup = sg.Window('Select folder containing audio files').Layout(load_data_layout)
main_window = sg.Window('Main Menu').Layout(main_layout)

#main window
while True:
	event, values = main_window.read()
	print('event: %s\nvalues: %s' % (event, values))
	if event in ('Load Data'):
		#pop up load window
		while True:
			ld_event, ld_values = load_data_popup.read()
			#print('ld_event: %s\nld_values: %s' % (ld_event, ld_values))
			if ld_event in ('OK'):
				
				


				wav_dir = ld_values['_FILES_'].split(';')[0]

				print('### SELECTED FOLDER ###')
				print(ld_values['_FILES_'].split(';')[0])

				print('### SELECTED FILES ###')
				for file_name in os.listdir(wav_dir):
					if file_name.endswith(".wav"):
						print(file_name)



				#create file storing wav file transformations
				if not os.path.exists('./png_scalogram'):
					os.mkdir('./png_scalogram')

				if not os.path.exists('./wav_transform'):
					os.mkdir('./wav_transform')

				png_sav_dir = './png_scalogram'
				wav_sav_dir = './wav_transform'




				###########################################################
				### PASS FILES TO DATA PIPELINE                         ###
				###########################################################

				WavPipeline.processPip(wav_dir,wav_sav_dir,png_sav_dir, split_wav = True)



				if ld_event in (None, 'Cancel'):
					load_data_popup.close()
					break
					if event in (None, 'Exit'):
						break


#TODO: allow ability to select and load multiple files
#TODO: 



main_window.close()
