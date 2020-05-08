import PySimpleGUI as sg
import os
import tempfile
import gzip
import shutil
import glob
import time

from scalogram.pipeline import WavPipeline
from scalogram.dataset import Dataset
from scalogram.testgan import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use('TkAgg')

#for settings
from json import (load as jsonload, dump as jsondump)

from notify_run import Notify

import queue
import threading

import gc 	# garbage collector for threads


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
DEFAULT_SETTINGS = {'theme': "DarkBlue3", 'debug': False, 'notify': False, 'notifylink': None}
SETTINGS_KEYS_TO_ELEMENT_KEYS = {'theme': '-THEME-', 'debug': '-DEBUG-', 'notify' : '-NOTIFY-', 'notifylink' : '-NOTIFYLINK-'}

nav_btn_size = (7,1)
menu_btn_size = (30,2)

multithreaded = False

def create_main_window(settings):
	sg.theme(settings['theme'])

	main_layout = [
	[sg.Text('Main Menu')],
	[sg.Button('Process Data',size=menu_btn_size)],
	[sg.Button('Create Dataset',size=menu_btn_size)],
	[sg.Button('GAN',size=menu_btn_size)],
	[sg.Exit(size=nav_btn_size), sg.Button('Settings', size=nav_btn_size)]
	]

	return sg.Window('ChirpGAN', main_layout, resizable = False)

def create_gan_window():
	
	gan_layout = [
		[sg.Text("GAN Menu")],
		[sg.Button("Train new models", size=menu_btn_size)],
		[sg.Button("Generate images", size=menu_btn_size)],
		[sg.Button("Cancel", size=nav_btn_size)]
	]

	return sg.Window('GAN Menu', gan_layout, resizable=True)

	
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

	theme = settings['theme']
	debug = settings['debug']
	notify_run = settings['notify']
	notifylink = settings['notifylink']
	
	sg.theme(theme)

	def TextLabel(text): return sg.Text(text+':', justification='l', size=(5,1))

	layout = [  [sg.Text('Settings', font='Any 15')],
				[TextLabel('Theme'), sg.Combo(sg.theme_list(), default_value = theme, size=(20, 20), key='-THEME-')],
				[sg.Checkbox('Developer Mode', default = debug, key='-DEBUG-')],
				[sg.Checkbox('Web Notification', default = notify_run, change_submits = True, enable_events=True, key ='-NOTIFY-')],
				[sg.Text('\tLink: '), sg.Text(notifylink, size=(30,1), enable_events=True, justification='l', key='-NOTIFYLINK-')],
				[sg.Button('Default Settings', size=(nav_btn_size[0]*2,nav_btn_size[1]))],
				[sg.Button('Save', size=nav_btn_size), sg.Button('Cancel', size=nav_btn_size)]
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
			sg.ProgressBar(total_files*3, orientation='h', size=(20,20), key='progressbar_p'),
			sg.Text('Number of processes:',  size=(20,None)),
			sg.Text(size=(10,None), key='proc_c')
		],
		[
			sg.ProgressBar(total_files, orientation='h', size=(20,20), key='progressbar_f'), 
			sg.Text('Files processed:',  size=(20,None)), 
			sg.Text(size=(10,None), key='file_c') # show progress in %
		],
		[sg.Button('Start', size=nav_btn_size), sg.Cancel(size=nav_btn_size)]
	]

	if debug:
		debug_text = [sg.Text('Debug output:')]
		debug_output = [sg.Output(size=(80,10))]
		pg_layout.insert(3, debug_output)
		pg_layout.insert(3, debug_text)

	return sg.Window('File Processing',pg_layout,resizable = False)


# GAN training progress window
def create_gan_train_window():

	gan_train_layout = [
		[sg.Text('GAN training in progress!')],
		[sg.Text('Progress:')],
		[sg.Output(size=(80,10))],
		[sg.Button('Start', size=nav_btn_size), sg.Button('Cancel', size=nav_btn_size)]
	]

	return sg.Window('New GAN model in training', gan_train_layout, resizable=False)

def create_plt_window(modelname):

	plt_window_layout = [
		[sg.Text('Generated scalograms:')],
		[sg.Text('Model: %s' % modelname)],
		[sg.Canvas(key='-CANVAS-')],
		[sg.Button('Ok', size=nav_btn_size), sg.Button('New', size=nav_btn_size), sg.Button('Save', size=nav_btn_size)]
	]

	return sg.Window('GAN: Generate images', plt_window_layout, element_justification='center', finalize=True)

def draw_figure(canvas, figure):
	figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
	figure_canvas_agg.draw()
	figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
	return figure_canvas_agg

def generate_images_grid(modelname):
	fig = main_generate(modelname)
	return fig


# creates data loading popup window based on boolean to render warning message
def create_load_data_popup(settings, wav_warning=False, empty_warning=False):
	wav_warn_text = [sg.Text(text='  *Make sure folder only contains .wav files.', text_color='#d9534f')]
	empty_warn_text = [sg.Text(text='  *Please select a folder.', text_color='#d9534f')]

	sg.theme(settings['theme'])


	load_data_layout = [
		[sg.Text('Folder of bird vocalization files to load: ')],
		[sg.Input(key='_FILES_'), sg.FolderBrowse(size=nav_btn_size)], 
		[sg.OK(size=nav_btn_size), sg.Cancel(size=nav_btn_size)]
	]

	if wav_warning:
		load_data_layout.insert(1, wav_warn_text)
	
	if empty_warning:
		load_data_layout.insert(1, empty_warn_text)

	return sg.Window('Select folder containing audio files').Layout(load_data_layout)


def main_data_process(listwavs, totalwavs, wave_sav_dir, png_sav_dir, total_files, pg_window):
	"""
	Single-threaded version of data processing pipeline
	"""

	i=0
	
	notify = Notify()

	for splitwav in listwavs:
		if splitwav.endswith('.wav'):

			notify.send('Processing file: (%d/%d)' % (i+1,total_files))
			
			print('\nInitiating data processing pipeline')

			p = (i*3)

			wavname = os.path.join(wave_sav_dir, splitwav)			  # .wav file with full path
			fname = splitwav[:splitwav.rfind('.')]					  # remove .wav extension
			scalname = os.path.join(png_sav_dir , '%s.scal' % fname)	# .scal file with full path
			scalgzname = scalname + '.gz'							   # .scal.gz file
			mp3name = os.path.join(wave_sav_dir, fname + '.mp3')		# .mp3 name


			###################
			### WAV -> SCAL ###
			###################
			
			## message
			print('\nwavname: %s\nfname: %s\nscalname: %s\nscalgzname: %s\nmp3name: %s' % (wavname, fname, scalname, scalgzname, mp3name)) 
			print('\nStarting Operation: WAV TO SCAL')
			pg_window.read(timeout=10)

			time.sleep(2)

			WavPipeline.wavToScl(wavname, scalname, scalgzname, mp3name)

			print('Complete: WAV TO SCAL')

			## pb update  -- finished wav -> scal
			update_text = ['(%d/%d)' % (p+1,(total_files*3)), '(%d/%d)' % (i,total_files),p+1,i]

			# update text
			pg_window['proc_c'].update(update_text[0])
			pg_window['file_c'].update(update_text[1])

			# update bar
			pg_window['progressbar_p'].UpdateBar(update_text[2])
			pg_window['progressbar_f'].UpdateBar(update_text[3])
			pg_window.read(timeout=10)



			###################
			### SCAL -> PNG ###
			###################

			## message
			print('\nStarting Operation: SCAL TO PNG')
			pg_window.read(timeout=10)

			time.sleep(2)
			
			WavPipeline.scalToPng(fname,scalname,scalgzname, png_sav_dir)

			print('Complete: SCAL TO PNG')


			## pb update  -- finished scal -> png
			update_text = ['(%d/%d)' % (p+2,(total_files*3)), '(%d/%d)' % (i,total_files),p+2,i]
			
			# update text
			pg_window['proc_c'].update(update_text[0])
			pg_window['file_c'].update(update_text[1])

			# update bar
			pg_window['progressbar_p'].UpdateBar(update_text[2])
			pg_window['progressbar_f'].UpdateBar(update_text[3])
			pg_window.read(timeout=10)


			###################
			###  FLOOD PNG  ###
			###################

			## message
			print('\nStarting Operation: PNG FLOOD-FILL')
			pg_window.read(timeout=10)

			time.sleep(2)

			#gc.collect()
			WavPipeline.flood_png(fname, png_sav_dir)

			print('Complete: PNG FLOOD-FILL')
			
			i+=1
			
			## pb update signal -- finished flooding png
			update_text = ['(%d/%d)' % (p+3,(total_files*3)), '(%d/%d)' % (i,total_files),p+3,i]
			
			# update text
			pg_window['proc_c'].update(update_text[0])
			pg_window['file_c'].update(update_text[1])

			# update bar
			pg_window['progressbar_p'].UpdateBar(update_text[2])
			pg_window['progressbar_f'].UpdateBar(update_text[3])
			pg_window.read(timeout=10)

	
	notify.send('Data processing complete')


####################################
### FUNCTION TO BE MULTITHREADED ### sourced from https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Multithreaded_Long_Tasks.py
####################################

def main_op_thread(listwavs, totalwavs, wave_sav_dir, png_sav_dir, total_files, gui_queue):
	"""
	multithreaded implementation of data processing pipeline 
	Args:
		gui_queue: Queue to communicate back to GUI with messages
	"""
	i=0
	
	for splitwav in listwavs:
		if splitwav.endswith('.wav'):


			### message - progress report
			# gui_queue.put('(%d/%d)' % (i, totalwavs))

			# track process
			p = (i*3)

			wavname = os.path.join(wave_sav_dir, splitwav)			  # .wav file with full path
			fname = splitwav[:splitwav.rfind('.')]					  # remove .wav extension
			scalname = os.path.join(png_sav_dir , '%s.scal' % fname)	# .scal file with full path
			scalgzname = scalname + '.gz'							   # .scal.gz file
			mp3name = os.path.join(wave_sav_dir, fname + '.mp3')		# .mp3 name



			###################
			### WAV -> SCAL ###
			###################
			
			## message
			gui_queue.put('wavname: %s\nfname: %s\nscalname: %s\nscalgzname: %s\nmp3name: %s' % (wavname, fname, scalname, scalgzname, mp3name)) 
			gui_queue.put('Starting Operation: WAV TO SCL\n')

			WavPipeline.wavToScl(wavname, scalname, scalgzname, mp3name)

			## pb update signal -- finished wav -> scal
			update_text = ['(%d/%d)' % (p+1,(total_files*3)), '(%d/%d)' % (i,total_files),p+1,i]
			gui_queue.put(update_text)
			

			###################
			### SCAL -> PNG ###
			###################

			## message
			gui_queue.put('SCL TO PNG\n')
			
			WavPipeline.scalToPng(fname,scalname,scalgzname, png_sav_dir)


			## pb update signal -- finished scal -> png
			update_text = ['(%d/%d)' % (p+2,(total_files*3)), '(%d/%d)' % (i,total_files),p+2,i]
			gui_queue.put(update_text)


			###################
			###  FLOOD PNG  ###
			###################

			## message
			gui_queue.put('PNG FLOOD FILL\n')
			"""

			# pngname = os.path.join(png_sav_dir , '%s.png' % fname)

			#gc.collect()
			WavPipeline.flood_png(fname, png_sav_dir)
			time.sleep(5)
			gui_queue.put('COMPLETED FLOOD')

			i+=1
			
			## pb update signal -- finished flooding png
			update_text = ['(%d/%d)' % (p+3,(total_files*3)), '(%d/%d)' % (i,total_files),p+3,i]
			gui_queue.put(update_text)
			"""


	# gui_queue.put(42) # thread completion code
	# time.sleep(5)
	

def gan_train_thread(dataset):

	gan_train_main(dataset)



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
			#gc.collect()

		if load_data_popup is None:
			load_data_popup = create_load_data_popup(settings)
			#gc.collect()

		event, values = main_window.read()
		#print('event: %s\nvalues: %s' % (event, values))
		
		if event == ('Exit'):
			main_window.close()
			main_window = None
			#gc.collect()
			break

		if event in ('Settings'):
			# close main window
			main_window.close()
			main_window = None
			#gc.collect()

			settings_window = create_settings_window(settings)

			while True:
				event, values = settings_window.read()
				print(event)
				print(values)

				if event in (None, 'Quit', 'Cancel'):
					settings_window.close()
					settings_window = None
					#gc.collect()
					break
					# break

				# if event in ('Cancel'): 
				# 	settings_window.close()

				if event == 'Default Settings':
					settings_window.close()
					##gc.collect()

					# default settings
					default_settings(SETTINGS_FILE)
					settings = load_settings(SETTINGS_FILE, DEFAULT_SETTINGS)

				
				if event == 'Save':
					
					# for some reason values does not contain the key for Text elements
					values['-NOTIFYLINK-'] = settings_window['-NOTIFYLINK-'].DisplayText

					settings_window.close()
					settings_window = None
					#gc.collect()

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
					notify = Notify()
					notify.send('Notifications will appear here.')

					webbrowser.open_new(link)

			continue


		###################################
		####### CREATE DATASET FLOW #######
		###################################
		if event in ('Create Dataset'):
			folder_path = sg.popup_get_folder("Please select the folder of flooded scalogram files", title="Select Folder for dataset")

			sg.popup('Creating dataset...Please wait')
			
			Dataset(folder_path)

			sg.popup('Dataset Created!')

		#########################
		####### GAN FLOW ########
		#########################
		if event in ('GAN'):
			main_window.close()
			main_window = None

			gan_window = None

			while True:
				
				if gan_window is None:
					gan_window = create_gan_window()
				else:
					break
				
				gan_event, gan_values = gan_window.read()

				if gan_event in (None, 'Quit', 'Cancel'):
					gan_window.close()
					break

				if gan_event.startswith('Generate'): # generate images
					gan_window.close()

					modelname = sg.popup_get_file("Please select a trained GAN model", title="Generate images from GAN model")

					if modelname in (None, 'Cancel'):
						gan_window = None
						continue

					plt_window = create_plt_window(modelname)
					fig = generate_images_grid(modelname)
					fig_canvas_agg = draw_figure(plt_window['-CANVAS-'].TKCanvas, fig)

					while True:
						plt_event, plt_values = plt_window.read()

						if plt_event in (None, 'Quit', 'Cancel', 'Ok'):
							plt_window.close()
							plt_window = None
							break


						if plt_event in ('New'):
							fig = generate_images_grid(modelname)
							fig_canvas_agg.get_tk_widget().pack_forget()
							fig_canvas_agg = draw_figure(plt_window['-CANVAS-'].TKCanvas, fig)
							_, _ = plt_window.read(timeout=10)
							continue


						if plt_event in ('Save'):
							namefile = sg.PopupGetFile('Enter filename', save_as=True)

							if namefile:
								try:
									fig.savefig(namefile)
									# plt_window.close()
									# plt_window = None
									sg.popup_quick_message('Image saved!', keep_on_top=True, auto_close_duration=2)
									time.sleep(2)
								except Exception as e:
									sg.popup('Error saving figure')
										

				if gan_event.startswith('Train'): # train new models
					gan_window.close()

					# select dataset file
					dataset = sg.popup_get_file("Please select a .npz dataset file", title="Train new GAN model: Load Dataset")

					if dataset in (None, 'Cancel'): 
						gan_window = None
						continue

					gan_train_window = create_gan_train_window()

					gan_train_started = False
					thread = None

					while True:
						gt_event, gt_values = gan_train_window.read(timeout=10)

						if gt_event in (None, 'Quit', 'Cancel'):
							if gan_train_started: thread.join()
							gan_train_window.close()
							gan_train_window = None
							gan_train_started = False

							sg.popup_quick_message('Cancelled. Returning to main menu.', keep_on_top=True, auto_close_duration=2)
							time.sleep(2)

							break

						if gt_event in ('Start') and not gan_train_started:
							gan_train_main(dataset)
							gan_train_started = True

						# if gt_event in ('Start') and not gan_train_started:
						# 	try:
						# 		thread = threading.Thread(target=gan_train_main, args=(dataset,), daemon=True)
						# 		thread.start()
						# 		gan_train_started = True
						# 	except Exception as e:
						# 		print('Error starting thread: ', e)

		if event in ('Process Data'):
			main_window.close() # close main menu
			main_window = None
			#gc.collect()

			# boolean for showing warning message in load data layout
			select_folder_warning = False
			wav_only_warning = False

			load_data_popup = None

			while True: 
				#pop up load window

				if load_data_popup is None:
					load_data_popup = create_load_data_popup(settings, wav_only_warning, select_folder_warning)
				else:
					break

				
				ld_event, ld_values = load_data_popup.read()
				#print('ld_event: %s\nld_values: %s' % (ld_event, ld_values))

				if ld_event == 'Cancel':
					load_data_popup.close()
					# load_data_popup = None
					#gc.collect()
					break
			
				if ld_event in ('OK'): 	# clicked OK without selecting folder
					if ld_values['_FILES_']=='':
						load_data_popup.close()
						load_data_popup = None
						#gc.collect()
						select_folder_warning = True
						continue

					select_folder_warning = False
					
					# close load_data_popup
					load_data_popup.close()
					# load_data_popup = None
					#gc.collect()

					# print(ld_values)


					wave_dir = ld_values['_FILES_'].split(';')[0]

					print('### SELECTED FOLDER ###')
					print(wave_dir)

					print('### SELECTED FILES ###')
					# for file_name in os.listdir(wave_dir):
					# 	if file_name.endswith(".wav"):
					# 		print(file_name)
					
					# check for non .wav files in selected folder
					total_num_files = len(os.listdir(wave_dir))
					total_num_wavs = len(glob.glob1(wave_dir, '*.wav'))
					# if non .wav files exist, warn user and return to load_data window
					wav_only_warning = total_num_files != total_num_wavs

					if not wav_only_warning:

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

						# print('SPLITTING\n')

						# org_wav = os.stat(wave_dir + "/test.wav")
						# print(f'File size in Bytes is {org_wav.st_size}')


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
						gui_queue = queue.Queue()

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
						started = False
						if multithreaded:
							print('MODE: MULTITHREADED')
							# multithreaded -- gui is responsive but may (will most definitely) crash 				
							while True:
								event, values = pg_window.read(timeout=100)

								if event in (None, 'Exit', 'Cancel'):
									print('CANCELLED, EXITING')
									pg_window.close()
									pg_window = None
									sg.popup_quick_message('Cancelled. Returning to main menu.', keep_on_top=True, auto_close_duration=1)
									time.sleep(1)
									break

								elif event.startswith('Start') and not started: # check for thread already spun up
									try:
										print('STARTING THREAD')
										thread = threading.Thread(target=main_op_thread, 
															args=(listwavs, totalwavs, wave_sav_dir, png_sav_dir, total_files, gui_queue), 
															daemon=True)
										thread.start()
										
										started = True
									except Exception as e:
										print('Error starting work thread')
								# elif event == 'Check responsive':
								# 	print('GUI is responsive')

								# check for incoming messages from thread
								try:
									message = gui_queue.get_nowait()
								except queue.Empty:
									message = None
								
								# check if message exists
								if message:
									# CHECK FOR SPECIFIC MESSAGES TO UPDATE PROGRESS BAR VALUES
									if isinstance(message, int) and message==42: 
										thread.join()
										print('thread joined')
										pg_window.close()
										pg_window = None
										sg.popup_quick_message("Data Processing Complete", keep_on_top=True, auto_close_duration=2)
										time.sleep(2)
										break
									elif isinstance(message, str): # if string instance print it
										print(message)
									else: # otherwise, it is an opcode to update the progress bar
										print(message)
										proc_c_text = message[0]
										file_c_text = message[1]
										
										p_c = message[2]
										f_c = message[3]

										# update text
										pg_window['proc_c'].update(proc_c_text)
										pg_window['file_c'].update(file_c_text)

										# update bar
										process_count.UpdateBar(p_c)
										progress_bar.UpdateBar(f_c)

						else:
							print('MODE: SINGLETHREADED')
							# single threaded -- gui will not be responsive until each step is complete.
							event, values = pg_window.read()

							if event in (None, 'Exit', 'Cancel'):
								print('CANCELLED, EXITING')
								pg_window.close()
								pg_window = None
								sg.popup_quick_message('Cancelled. Returning to main menu.', keep_on_top=True, auto_close_duration=1)
								time.sleep(1)
								break

							elif event.startswith('Start') and not started:
								started = True

								# execute single-threaded processing pipeline 
								main_data_process(listwavs, totalwavs, wave_sav_dir, png_sav_dir, total_files, pg_window)

								pg_window.close()
								pg_window = None

								sg.popup('Completion window', 'The provided data has successfully been processed!\nFind the results in your local directory.')


						# TODO: SEPARATELY CALL EACH FUNCTION IN THE PIPELINE
						# TODO: UPDATE THE GUI AND THE USER ON THE PROCESS OF EACH FUNCTION CALL
						# TODO: UPSCALE THE GUI SIZE SO IT IS NOT TIGHTLY FIT TO THE CURRENT GUI ELEMENTS -> MAKE IT MORE USER-FRIENDLY AND NAVIGABLE

						if ld_event in (None, 'Cancel'):
							load_data_popup.close()
							load_data_popup = None
							#gc.collect()
							break
					else:
						print('non .wav files detected')
						load_data_popup = None
						#gc.collect()

				if event in (None, 'Exit'):
					main_window.close()
					main_window = None
					#gc.collect()



if __name__ == '__main__':
	main()