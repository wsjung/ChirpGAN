import PySimpleGUI as sg
import os
import tempfile
import gzip
import shutil
import glob
import time


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
	#print('event: %s\nvalues: %s' % (event, values))
	
	if event == ('Exit'):
		main_window.close()


	if event in ('Load Data'):
		#pop up load window
		while True:


			ld_event, ld_values = load_data_popup.read()
			#print('ld_event: %s\nld_values: %s' % (ld_event, ld_values))
			if ld_event == 'Cancel':
				load_data_popup.close()


			if ld_event in ('OK'):
				
				


				wave_dir = ld_values['_FILES_'].split(';')[0]

				print('### SELECTED FOLDER ###')
				print(ld_values['_FILES_'].split(';')[0])

				print('### SELECTED FILES ###')
				for file_name in os.listdir(wave_dir):
					if file_name.endswith(".wav"):
						print(file_name)



				#create file storing wav file transformations
				if not os.path.exists('./png_scalogram'):
					os.mkdir('./png_scalogram')

				if not os.path.exists('./wav_transform'):
					os.mkdir('./wav_transform')

				png_sav_dir = './png_scalogram'
				wave_sav_dir = './wav_transform'




				###########################################################
				### PASS FILES TO DATA PIPELINE                         ###
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

				#define progress bar window
				pg_layout = [[sg.Text('Processing files')],
							 [sg.ProgressBar(total_files, orientation='h', size=(20,20), key='progressbar_f')],
							 [sg.Text('Files processed:'), sg.Text(size=(15,1), key='file_c')],
							 [sg.ProgressBar(total_files*3, orientation='h', size=(20,20), key='progressbar_p')],
							 [sg.Text('Number of processes:'), sg.Text(size=(15,1), key='proc_c')],
							 [sg.Cancel()]]

				pg_window = sg.Window('File Processing').Layout(pg_layout)
				progress_bar = pg_window['progressbar_f']
				process_count = pg_window['progressbar_p']

				pg_window.read(timeout=10)

				process_count.UpdateBar(0) 
				progress_bar.UpdateBar(0) 

				pg_window['file_c'].update('(0/%d)' % total_files)
				pg_window['proc_c'].update('(0/%d)' % (total_files*3))

				pg_window.read(timeout=10)


				try:
					for splitwav in listwavs:
						print("TEST")
						print(splitwav)
						if splitwav.endswith('.wav'):

							### report progress
							print('(%d/%d)' % (i, totalwavs))
							#track process
							p = ((i-1)*3)

							wavname = os.path.join(wave_sav_dir, splitwav)              # .wav file with full path
							fname = splitwav[:splitwav.rfind('.')]                      # remove .wav extension
							scalname = os.path.join(png_sav_dir , '%s.scal' % fname)    # .scal file with full path
							scalgzname = scalname + '.gz'                               # .scal.gz file
							mp3name = os.path.join(wave_sav_dir, fname + '.mp3')        # .mp3 name

												
							print('wavname: %s\nfname: %s\nscalname: %s\nscalgzname: %s\nmp3name: %s' % (wavname, fname, scalname, scalgzname, mp3name)) 

							print('WAV TO SCL\n')

							#wav_s = os.stat(wavname)
							#size_wav += wav_s.st_size


							#start = time.time()
							WavPipeline.wavToScl(wavname, scalname, scalgzname, mp3name)
							#stop =  time.time()

							#time_wavToScl += (stop-start)  

							process_count.UpdateBar(p+1) 
							pg_window['proc_c'].update('(%d/%d)' % (p+1,(total_files*3)))
							pg_window.read(timeout=10)
					
							print('SCL TO PNG\n')

							#scl_s = os.stat(scalname)
							#size_scl += scl_s.st_size
							
							#start = time.time()
							WavPipeline.scalToPng(fname,scalname,scalgzname, png_sav_dir )
							#stop = time.time()

							#time_sclToPng += (stop-start)

							process_count.UpdateBar(p+2) 
							pg_window['proc_c'].update('(%d/%d)' % (p+2,(total_files*3)))
							pg_window.read(timeout=10)

							print('PNG FLOOD FILL\n')

							pngname = os.path.join(png_sav_dir , '%s.png' % fname)

							#png_s = os.stat(pngname)
							#size_png += png_s.st_size

							#start = time.time()
							WavPipeline.flood_png(fname, png_sav_dir )
							#stop = time.time()

							process_count.UpdateBar(p+3) 
							pg_window['proc_c'].update('(%d/%d)' % (p+3,(total_files*3)))
							pg_window.read(timeout=10)

							#time_flood += (stop-start)
							
							

							progress_bar.UpdateBar(i)  
							pg_window['file_c'].update('(%d/%d)' % (i,total_files))
							pg_window.read(timeout=10)

							i+=1

				except:
					print('################## ERROR DURING DATA PROCESSING ################')
					exit(-1)


				pg_window.close()

				# TODO: SEPARATELY CALL EACH FUNCTION IN THE PIPELINE
				# TODO: UPDATE THE GUI AND THE USER ON THE PROCESS OF EACH FUNCTION CALL
				# TODO: UPSCALE THE GUI SIZE SO IT IS NOT TIGHTLY FIT TO THE CURRENT GUI ELEMENTS -> MAKE IT MORE USER-FRIENDLY AND NAVIGABLE



				if ld_event in (None, 'Cancel'):
					load_data_popup.close()
					break
					if event in (None, 'Exit'):
						break

			if event in (None, 'Exit'):
				main_window.close()




load_data_popup.close()
main_window.close()
