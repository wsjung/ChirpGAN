from data_process_wav import DataSplitter
from scalogram import Scalogram
from floodfill import Floodfill
import sys
import os
from notify_run import Notify
import gzip
import shutil
import glob
import logging

class WavPipeline:

###########################################################
### run split wav --> scal --> png --> flood in batches ###
###########################################################


    def split(wav_dir, wav_save_dir, png_save_dir):

        # notify.send('running batches of size %d' % batch_size)

        print('starting full conversion') # log

        listwavs = os.listdir(wav_dir)
        totalwavs = len(glob.glob1(wav_save_dir, '*.wav'))
        i=1

        try:
            for splitwav in listwavs:
                if splitwav.endswith('.wav'):

                    ### report current batch progress
                    # print('batch progress: (%d/%d)' % (batch_counter, batch_size)
                    # notify.send('batch progress: (%d/%d)' % (batch_counter, batch_size))
            
                    ### report progress
                    print('(%d/%d)' % (i, totalwavs))
                    #notify.send('(%d/%d)' % (i, totalwavs))
                    #logging.info('(%d/%d)' % (i, totalwavs)) # log

                    wavname = os.path.join(wav_save_dir, splitwav)              # .wav file with full path
                    fname = splitwav[:splitwav.rfind('.')]                      # remove .wav extension
                    scalname = os.path.join(png_save_dir, '%s.scal' % fname)    # .scal file with full path
                    scalgzname = scalname + '.gz'                               # .scal.gz file
                    mp3name = os.path.join(wav_save_dir, fname + '.mp3')        # .mp3 name
                                        
                    #print('wavname: %s\nfname: %s\nscalname: %s\nscalgzname: %s\nmp3name: %s' % (wavname, fname, scalname, scalgzname, mp3name)) 