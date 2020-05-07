from scalogram.data_process_wav import DataSplitter
from scalogram.scalogram import Scalogram
from scalogram.floodfill import Floodfill
import sys
import os
import gzip
import shutil
import glob
import time
import numpy as np
from notify_run import Notify
from PIL import Image


class WavPipeline():

    ###########################################################
    # g  et total file size of all files for runtime estimate #
    ###########################################################
    # def file_sizes(dir, ext):

    ###########################################################
    ### rsplit wav files                                    ###
    ###########################################################


    def split(wav_dir,wav_save_dir):

        data_splitter = DataSplitter(130, wav_dir, wav_save_dir)



    # ###########################################################
    # ### run entire WavPipeline                              ###
    # ###########################################################
    # def processPip(wav_dir,wav_save_dir,png_save_dir, split_wav = True):


    #     #print('starting full conversion') # log


    #     #print('SPLITTING\n')

    #     org_wav = os.stat(wav_dir + "/test.wav")
    #     #print(f'File size in Bytes is {org_wav.st_size}')


    #     start = time.time()
    #     if (split_wav):
    #         WavPipeline.split(wav_dir, wav_save_dir)
    #     stop = time.time()

    #     time_split= stop-start

    #     listwavs = os.listdir(wav_save_dir)
    #     totalwavs = len(glob.glob1(wav_save_dir, '*.wav'))
    #     i=1

    #     size_wav = 0
    #     size_scl = 0
    #     size_png = 0


    #     time_wavToScl = 0
    #     time_sclToPng = 0
    #     time_flood = 0

    #     try:
    #         for splitwav in listwavs:
    #             if splitwav.endswith('.wav'):
            
    #                 ### report progress
    #                 #print('(%d/%d)' % (i, totalwavs))

    #                 wavname = os.path.join(wav_save_dir, splitwav)              # .wav file with full path
    #                 fname = splitwav[:splitwav.rfind('.')]                      # remove .wav extension
    #                 scalname = os.path.join(png_save_dir, '%s.scal' % fname)    # .scal file with full path
    #                 scalgzname = scalname + '.gz'                               # .scal.gz file
    #                 mp3name = os.path.join(wav_save_dir, fname + '.mp3')        # .mp3 name
                                        
    #                 #print('wavname: %s\nfname: %s\nscalname: %s\nscalgzname: %s\nmp3name: %s' % (wavname, fname, scalname, scalgzname, mp3name)) 

    #                 #print('WAV TO SCL\n')

    #                 wav_s = os.stat(wavname)
    #                 size_wav += wav_s.st_size


    #                 start = time.time()
    #                 WavPipeline.wavToScl(wavname, scalname, scalgzname, mp3name)
    #                 stop =  time.time()

    #                 time_wavToScl += (stop-start)    

    #                 #print('SCL TO PNG\n')

    #                 scl_s = os.stat(scalname)
    #                 size_scl += scl_s.st_size
                    
    #                 start = time.time()
    #                 WavPipeline.scalToPng(fname,scalname,scalgzname, png_save_dir)
    #                 stop = time.time()

    #                 time_sclToPng += (stop-start)

    #                 #print('PNG FLOOD FILL\n')

    #                 pngname = os.path.join(png_save_dir, '%s.png' % fname)

    #                 png_s = os.stat(pngname)
    #                 size_png += png_s.st_size

    #                 start = time.time()
    #                 WavPipeline.flood_png(fname, png_save_dir)
    #                 stop = time.time()

    #                 time_flood += (stop-start)

    #                 i+=1

    #     except:
    #         #print('################## ERROR DURING DATA PROCESSING ################')
    #         exit(-1)


    #     #print("SIZES: WAV:%d WAV_s:%d  SCL:%d PNG%d\n", (org_wav.st_size, size_wav, size_scl, size_png))
    #     #print("TIME: WAV:%d WAV_s:%d  SCL:%d PNG%d\n", (time_split, time_wavToScl, time_sclToPng, time_flood))


    ####################
    ### wav --> scal ###
    ####################
    def wavToScl(wavname,scalname,scalgzname,mp3name):

        notify = Notify()

        #print('\nstarting wav -> scal transformation')
        notify.send('\nNOTIFY: starting wav -> scal transformation')

        ### check for already existing .scal file
        if os.path.exists(scalname) or os.path.exists(scalgzname):
            #print("SCAL file or gz %s already exists" % scalname)
            notify.send("SCAL file or gz %s already exists" % scalname)

        else:
            ################################################################
            ### create the scal file
            #print("Creating SCAL file from \"" + wavname + "\".")
            scal = Scalogram(wavname)
            scal.write_to_file(filename=scalname)
            #print("   ", scal)
            #print('scalfile created') # log
   

            ################################################################
            ### compress .wav file once converted to .scal file
            #print('compressing wav file %s' % wavname)
            #print('compressing wav file %s' % wavname) # log
            os.system('ffmpeg -i %s %s' % (wavname, mp3name))
            #print('wav -> mp3 compression complete')
            #print('wav -> mp3 compression complete') # log


    # Returns a byte-scaled image
    def bytescale(data, cmin=None, cmax=None, high=255, low=0):
        if data.dtype == np.uint8:
            return data

        if high > 255:
            raise ValueError("`high` should be less than or equal to 255.")
        if low < 0:
            raise ValueError("`low` should be greater than or equal to 0.")
        if high < low:
            raise ValueError("`high` should be greater than or equal to `low`.")

        if cmin is None:
            cmin = data.min()
        if cmax is None:
            cmax = data.max()

        cscale = cmax - cmin
        if cscale < 0:
            raise ValueError("`cmax` should be larger than `cmin`.")
        elif cscale == 0:
            cscale = 1

        scale = float(high - low) / cscale
        bytedata = (data - cmin) * scale + low
        return (bytedata.clip(low, high) + 0.5).astype(np.uint8)


    ####################
    ### scal --> png ###
    ####################
    def scalToPng(fname,scalname,scalgzname, png_save_dir):

        notify = Notify()

        #print('STARTING SCL TO PNG')
        notify.send('STARTING SCL TO PNG')

        pngname = os.path.join(png_save_dir, '%s.png' % fname)  # .png file with full path

        #print('\n##### starting scal -> png transformation')
        #print(pngname)


        ### check for already existing .png file
        if os.path.exists(pngname):
            #print("PNG file %s already exists" % pngname)
            notify.send("PNG file %s already exists" % pngname)
        else:
            ################################################################
            ### load the correct scal file (raw or gz)
            isScalGz = os.path.exists(scalgzname)
            if isScalGz:
                ### decompress .scal.gz
                with open(scalgzname, 'rb') as f_in:
                    with gzip.open(scalname, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                ## delete original scal file
                os.remove(scalgzname)
            
            sname = scalname

            ################################################################
            ### create the png file
            #print("Info on SCAL file \"" +sname+ "\":")
            scal = Scalogram(sname)
            #print('loaded scal')
            # #print("   ", scal)
            #argmax = scal.argmax()
            #argmin = scal.argmin()
            ##print("   max:", scal[argmax[0]][argmax[1]], "(t:", argmax[0], ", f:", argmax[1], ")")
            ##print("   min:", scal[argmin[0]][argmin[1]], "(t:", argmin[0], ", f:", argmin[1], ")")
            ##print("   mean:", scal.mean())
            
            print("WRITE TO PNG GOES HERE")
            # scal.write_to_png(filename=pngname)

            data = 1.0 - np.flipud(np.transpose(scal.data))

            bytedata = WavPipeline.bytescale(data)

            shape = (data.shape[1], data.shape[0])

            im = Image.frombytes('L', shape, bytedata.tostring())
            im.save(pngname, cmin=0.0, cmax=1.0)

            return
            
            #print('created pngfile')

    #################
    ### flood png ###
    #################
    def flood_png(fname, png_save_dir):

        pngname = os.path.join(png_save_dir, '%s.png' % fname)

        flood_dir = os.path.join(png_save_dir, 'flood')
        # create flooded png directory if doesn't exist
        if not os.path.isdir(flood_dir):
            print('creating flood directory', flush=True)
            os.mkdir(flood_dir)

        floodpngname = os.path.join(flood_dir, '%s_flooded.png' % fname)    # flooded .png file with full path
        print('\n##### starting flooding png')
        print(floodpngname)


        ### check for already existing flooded .png file
        if os.path.exists(floodpngname):
            print("FLOODED PNG file %s already exists" % floodpngname)
        else:
            print('Info on PNG file \'' + pngname + '\':')
            png = Floodfill(pngname)
            print('flooded')

            im = Image.fromarray(png.png_data)
            im.save(floodpngname)

            # png.write_to_png(filename=floodpngname)
            #print('wrote')


"""
#defaults
wav_dir = "../recordings"
wav_save_dir = "../wav_transform"
png_save_dir = "../png_scalogram"


#test inputs
wavname = '../wav_transform/ml-american-robin0.wav'
fname = 'ml-american-robin0'
scalname = '../png_scalogram/ml-american-robin0.scal'
scalgzname = '../png_scalogram/ml-american-robin0.scal.gz'
mp3name = '../wav_transform/ml-american-robin0.mp3'
pngname = '../png_scalogram/ml-american-robin0.png'


#WavPipeline.wavToScl(wavname,scalname,scalgzname,mp3name)
#WavPipeline.flood_png(fname,pngname, png_save_dir)
WavPipeline.processPip(wav_dir,wav_save_dir,png_save_dir)
"""