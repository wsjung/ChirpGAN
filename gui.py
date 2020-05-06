import PySimpleGUI as sg
import os
import tempfile
import gzip
import shutil
import glob
import time

from scalogram.pipeline import WavPipeline

#for settings
from json import (load as jsonload, dump as jsondump)

from notify_run import Notify

import queue
import threading


## TODO: CREATE SETTINGS WINDOW (SAVE/LOAD FROM JSON?)
###### TODO: (EN/DIS)ABLE DEVELOPER (DEBUG) MODE [CHECKBOX]
###### TODO: (EN/DIS)ABLE NOTIFY-RUN NOTIFICATIONS [CHECKBOX] (use enable_events for element-specific event listeners)
########## TODO: on (ENABLE), set notify-run settings visible
########## TODO: on (ENABLE), register notify-run with user device and display notification link
########## TODO: on (DISABLE), disable notify-run setttings 


################
# CONFIGS VARS #
################

#sg.theme('DarkAmber')	# color


#####################################
# FUNCTIONS FOR DYNAMIC GUI WINDOWS #
#####################################


#default settings parameters
SETTINGS_FILE = os.path.join(os.path.dirname('./'), r'.settings_file.cfg')
DEFAULT_SETTINGS = {'theme': sg.theme(), 'debug': False, 'notify': False, 'notifylink': None}
SETTINGS_KEYS_TO_ELEMENT_KEYS = {'theme': '-THEME-', 'debug': '-DEBUG-', 'notify' : '-NOTIFY-', 'notifylink' : '-NOTIFYLINK-'}


def create_main_window(settings):
	sg.theme(settings['theme'])

	main_layout = [
	[sg.Text('Main Menu')],
	[sg.Button('Load Data',size=(30,2)), sg.Button('Settings')],
	[sg.Exit()]
	]

	return sg.Window('ChirpGAN', main_layout, resizable = False)


# load single specified setting
def load_setting(settings_file, key):
	try:
		with open(settings_file, 'r') as f:
			settings = jsonload(f)
	except Exception as e:
		print('this should never print')
	return settings[key]

#ability to load setings from JSON
def load_settings(settings_file, default_settings):
	try:
		with open(settings_file, 'r') as f:
			settings = jsonload(f)
	except Exception as e:
		#setting config not found
		sg.popup_quick_message(f'exception {e}', 'No settings file found... will create one for you', keep_on_top=True, background_color='red', text_color='white')
		settings = default_settings
		save_settings(settings_file, settings, None)
	return settings

def default_settings(settings_file):
	with open(settings_file, 'w') as f:
		jsondump(DEFAULT_SETTINGS, f)
	sg.popup('Settings defaulted')

#write user settings to JSON
def save_settings(settings_file, settings, values, popup=False):
	if values:	  # if there are stuff specified by another window, fill in those values
		for key in SETTINGS_KEYS_TO_ELEMENT_KEYS:  # update window with the values read from settings file
			try:
				settings[key] = values[SETTINGS_KEYS_TO_ELEMENT_KEYS[key]]
			except Exception as e:
				print(f'Problem updating settings from window values. Key = {key}')

	with open(settings_file, 'w') as f:
		jsondump(settings, f)

	if popup:
		sg.popup('Settings saved')

#create settings window
def create_settings_window(settings):
	sg.theme(settings['theme'])


	debug = settings['debug']
	notify_run = settings['notify']
	notifylink = settings['notifylink']

	def TextLabel(text): return sg.Text(text+':', justification='l', size=(5,1))

	layout = [  [sg.Text('Settings', font='Any 15')],
				[TextLabel('Theme'), sg.Combo(sg.theme_list(), size=(20, 20), key='-THEME-')],
				[sg.Checkbox('Developer Mode', default = debug, key='-DEBUG-')],
				[sg.Checkbox('Web Notification', default = notify_run, change_submits = True, enable_events=True, key ='-NOTIFY-')],
				[sg.Text('\tLink: '), sg.Text(notifylink, size=(30,1), enable_events=True, justification='l', key='-NOTIFYLINK-')],
				[sg.Button('Default Settings')],
				[sg.Button('Save'), sg.Text('		     '), sg.Button('Cancel')]
				]

	window = sg.Window('Settings', layout, keep_on_top=True, finalize=True, resizable = False)

	for key in SETTINGS_KEYS_TO_ELEMENT_KEYS:   # update window with the values read from settings file
		try:
			window[SETTINGS_KEYS_TO_ELEMENT_KEYS[key]].update(value=settings[key])
		except Exception as e:
			print(f'Problem updating PySimpleGUI window from settings. Key = {key}', e)

	return window



#define progress bar window
def create_prog_bar_popup(settings, total_files):

	debug = settings['debug'] #TODO get from settings
	sg.theme(settings['theme'])


	pg_layout = [
		[sg.Text('Processing files')],
		[
			sg.ProgressBar(total_files, orientation='h', size=(20,20), key='progressbar_f'), 
			sg.Text('Files processed:',  size=(20,None)), 
			sg.Text(size=(10,None), key='file_c') # show progress in %
		],
		[
			sg.ProgressBar(total_files*3, orientation='h', size=(20,20), key='progressbar_p'),
			sg.Text('Number of processes:',  size=(20,None)),
			sg.Text(size=(10,None), key='proc_c')
		],
		[sg.Button('Start Op'), sg.Button('Check responsive'), sg.Cancel()]
	]

	if debug:
		debug_text = [sg.Text('Debug output:')]
		debug_output = [sg.Output(size=(80,10))]
		pg_layout.insert(3, debug_output)
		pg_layout.insert(3, debug_text)

	return sg.Window('File Processing',pg_layout,resizable = False)


# creates data loading popup window based on boolean to render warning message
def create_load_data_popup(settings, wav_warning=False, empty_warning=False):
	wav_warn_text = [sg.Text(text='  *Make sure folder only contains .wav files.', text_color='#d9534f')]
	empty_warn_text = [sg.Text(text='  *Please select a folder.', text_color='#d9534f')]

	sg.theme(settings['theme'])


	load_data_layout = [
		[sg.Text('Folder of bird vocalization files to load: ')],
		[sg.Input(key='_FILES_'), sg.FolderBrowse()], 
		[sg.OK(), sg.Text('				      '), sg.Cancel()]
	]

	if wav_warning:
		load_data_layout.insert(1, wav_warn_text)
	
	if empty_warning:
		load_data_layout.insert(1, empty_warn_text)

	return sg.Window('Select folder containing audio files').Layout(load_data_layout)

#TODO: allow ability to select and load multiple files



####################################
### FUNCTION TO BE MULTITHREADED ### sourced from https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Multithreaded_Long_Tasks.py
####################################

def main_op_thread(listwavs, totalwavs, wave_sav_dir, png_sav_dir, total_files, pg_window, debug, gui_queue, process_count):
	"""
	Args:
		gui_queue: Queue to communicate back to GUI with messages
	"""
	i=1

	for splitwav in listwavs:
		if debug:
			gui_queue.put("TEST")
			gui_queue.put('file: ', splitwav)
		if splitwav.endswith('.wav'):

			### report progress
			if debug: gui_queue.put('(%d/%d)' % (i, totalwavs))
			#track process
			p = ((i-1)*3)

			wavname = os.path.join(wave_sav_dir, splitwav)			  # .wav file with full path
			fname = splitwav[:splitwav.rfind('.')]					  # remove .wav extension
			scalname = os.path.join(png_sav_dir , '%s.scal' % fname)	# .scal file with full path
			scalgzname = scalname + '.gz'							   # .scal.gz file
			mp3name = os.path.join(wave_sav_dir, fname + '.mp3')		# .mp3 name


			if debug:				
				gui_queue.put('wavname: %s\nfname: %s\nscalname: %s\nscalgzname: %s\nmp3name: %s' % (wavname, fname, scalname, scalgzname, mp3name)) 
				gui_queue.put('WAV TO SCL\n')

			#wav_s = os.stat(wavname)
			#size_wav += wav_s.st_size


			#start = time.time()
			WavPipeline.wavToScl(wavname, scalname, scalgzname, mp3name)
			#stop =  time.time()

			#time_wavToScl += (stop-start)  

			process_count.UpdateBar(p+1) 
			pg_window['proc_c'].update('(%d/%d)' % (p+1,(total_files*3)))
			pg_window.read(timeout=100)

			if debug: gui_queue.put('SCL TO PNG\n')

			#scl_s = os.stat(scalname)
			#size_scl += scl_s.st_size
			
			#start = time.time()
			WavPipeline.scalToPng(fname,scalname,scalgzname, png_sav_dir )
			#stop = time.time()

			#time_sclToPng += (stop-start)

			process_count.UpdateBar(p+2) 
			pg_window['proc_c'].update('(%d/%d)' % (p+2,(total_files*3)))
			pg_window.read(timeout=10)

			if debug: gui_queue.put('PNG FLOOD FILL\n')

			pngname = os.path.join(png_sav_dir , '%s.png' % fname)

			#png_s = os.stat(pngname)
			#size_png += png_s.st_size

			#start = time.time()
			WavPipeline.flood_png(fname, png_sav_dir )
			#stop = time.time()

			process_count.UpdateBar(p+3)
			pg_window['proc_c'].update('(%d/%d)' % (p+3,(total_files*3)))
			pg_window.read(timeout=100)

			#time_flood += (stop-start)

			progress_bar.UpdateBar(i)  
			pg_window['file_c'].update('(%d/%d)' % (i,total_files))
			pg_window.read(timeout=100)

			i+=1




###############
#### ENTRY ####
###############

def main():
	change_settings = False

	main_window, load_data_popup, settings = None, None, load_settings(SETTINGS_FILE, DEFAULT_SETTINGS)
	DEBUG_MODE = settings['debug']

	while True:
		if main_window is None:
			main_window = create_main_window(settings)

		if load_data_popup is None:
			load_data_popup = create_load_data_popup(settings)

		event, values = main_window.read()
		#print('event: %s\nvalues: %s' % (event, values))
		
		if event == ('Exit'):
			main_window.close()
			break

		if event in ('Settings'):
			settings_window = create_settings_window(settings)

			while True:
				event, values = settings_window.read()
				print(event)
				print(values)

				if event in (None, 'Quit'):
					settings_window.close()
					break

				if event == 'Cancel': 
					settings_window.close()
					break
				if event == 'Default Settings':
					settings_window.close()

					main_window.close()
					main_window = None

					# default settings
					default_settings(SETTINGS_FILE)
				
				if event == 'Save':
					settings_window.close()

					main_window.close()
					main_window = None
					
					# for some reason values does not contain the key for Text elements
					values['-NOTIFYLINK-'] = settings_window['-NOTIFYLINK-'].DisplayText

					save_settings(SETTINGS_FILE, settings, values, popup=True)
					
					change_settings = True

					break

				print(load_setting(SETTINGS_FILE, 'notify'))

				if event == '-NOTIFY-': # register using notify-run
					if values['-NOTIFY-'] and not load_setting(SETTINGS_FILE, 'notify'):
						notify = Notify()
						endpointinfo = notify.register()

						endpointlink = str(endpointinfo).split('\n')[0][10:]

						settings_window['-NOTIFYLINK-'].Update(endpointlink)
					else:
						settings_window['-NOTIFYLINK-'].Update('N/A')

				if event == '-NOTIFYLINK-' and values['-NOTIFY-']: # clicked on link
					import webbrowser

					link = settings_window['-NOTIFYLINK-'].DisplayText

					# send a welcome message
					notify.send('Notifications will appear here.')

					webbrowser.open_new(link)

			
			continue

		if event in ('Load Data'):
			#pop up load window

			# boolean for showing warning message in load data layout
			select_folder_warning = False
			wav_only_warning = False

			while True: 
				load_data_popup = create_load_data_popup(settings, wav_only_warning, select_folder_warning)
				ld_event, ld_values = load_data_popup.read()
				#print('ld_event: %s\nld_values: %s' % (ld_event, ld_values))

				if ld_event == 'Cancel':
					load_data_popup.close()
					break
			
				if ld_event in ('OK') and ld_values['_FILES_']=='': # clicked OK without selecting folder
					load_data_popup.close()
					select_folder_warning = True
				elif ld_event in ('OK'):
					select_folder_warning = False
					
					# close load_data_popup
					load_data_popup.close()

					print(ld_values)


					wave_dir = ld_values['_FILES_'].split(';')[0]

					print('### SELECTED FOLDER ###')
					print(wave_dir)

					print('### SELECTED FILES ###')
					for file_name in os.listdir(wave_dir):
						if file_name.endswith(".wav"):
							print(file_name)

					print('hello')
					
					# check for non .wav files in selected folder
					total_num_files = len(os.listdir(wave_dir))
					total_num_wavs = len(glob.glob1(wave_dir, '*.wav'))
					# if non .wav files exist, warn user and return to load_data window
					if total_num_files == total_num_wavs:
						wav_only_warning = False


						#create file storing wav file transformations
						if not os.path.exists('./png_scalogram'):
							os.mkdir('./png_scalogram')

						if not os.path.exists('./wav_transform'):
							os.mkdir('./wav_transform')

						png_sav_dir = './png_scalogram'
						wave_sav_dir = './wav_transform'


						###########################################################
						### PASS FILES TO DATA PIPELINE						 ###
						###########################################################

						print('SPLITTING\n')

						org_wav = os.stat(wave_dir + "/test.wav")
						print(f'File size in Bytes is {org_wav.st_size}')


						start = time.time()
						#TODO: add option to split wav files from GUI
						split_wav = True
						if (split_wav):
							WavPipeline.split(wave_dir, wave_sav_dir)
						stop = time.time()

						time_split= stop-start



						listwavs = os.listdir(wave_sav_dir)
						totalwavs = len(glob.glob1(wave_sav_dir, '*.wav'))
						i=1



						size_wav = 0
						size_scl = 0
						size_png = 0


						time_wavToScl = 0
						time_sclToPng = 0
						time_flood = 0

						total_files = 0

						try:
							for splitwav in listwavs:
								total_files += 1
						except:
							print('################## CANNOT FIND FILES ################')
							exit(-1)

						
						pg_window = create_prog_bar_popup(settings, total_files)
						# create communicate queue if debug mode
						gui_queue = None
						if DEBUG_MODE: gui_queue = queue.Queue()

						# pg_window = sg.Window('File Processing').Layout(pg_layout)
						progress_bar = pg_window['progressbar_f']
						process_count = pg_window['progressbar_p']

						pg_window.read(timeout=10)

						process_count.UpdateBar(0)
						progress_bar.UpdateBar(0)

						pg_window['file_c'].update('(0/%d)' % total_files)
						pg_window['proc_c'].update('(0/%d)' % (total_files*3))

						pg_window.read(timeout=10)

						# progress bar event loop
						while True:
							event, values = pg_window.read(timeout=100)

							if event in (None, 'Exit', 'Cancel'):
								print('CANCELLED, EXITING')
								break
							elif event.startswith('Start'):
								try:
									print('STARTING THREAD')
									threading.Thread(target=main_op_thread, 
														args=(listwavs, totalwavs, wave_sav_dir, png_sav_dir, total_files, pg_window, DEBUG_MODE, gui_queue, process_count), 
														daemon=True).start()
								except Exception as e:
									print('Error starting work thread')
							elif event == 'Check responsive':
								print('GUI is responsive')

							# check for incoming messages from thread
							if DEBUG_MODE:
								try:
									message = gui_queue.get_nowait()
								except queue.Empty:
									message = None

								# display message from queue
								if message:
									print(message)

						pg_window.close()
						# try:
							

						# except:
						#	 print('################## ERROR DURING DATA PROCESSING ################')
						#	 exit(-1)

						# TODO: SEPARATELY CALL EACH FUNCTION IN THE PIPELINE
						# TODO: UPDATE THE GUI AND THE USER ON THE PROCESS OF EACH FUNCTION CALL
						# TODO: UPSCALE THE GUI SIZE SO IT IS NOT TIGHTLY FIT TO THE CURRENT GUI ELEMENTS -> MAKE IT MORE USER-FRIENDLY AND NAVIGABLE



						if ld_event in (None, 'Cancel'):
							load_data_popup.close()
							break
							if event in (None, 'Exit'):
								break
					else:
						print('non .wav files detected')
						wav_only_warning = True

				if event in (None, 'Exit'):
					main_window.close()






if __name__ == '__main__':
	main()