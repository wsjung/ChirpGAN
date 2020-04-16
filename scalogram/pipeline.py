from scalogram.data_process_wav import DataSplitter
from scalogram.scalogram import Scalogram
from scalogram.floodfill import Floodfill
import sys
import os
import gzip
import shutil
import glob

class WavPipeline():

    ###########################################################
    ### rsplit wav files                                    ###
    ###########################################################
    def split(wav_dir,wav_save_dir):
        data_splitter = DataSplitter(130, wav_dir, wav_save_dir)



    ###########################################################
    ### run entire WavPipeline                              ###
    ###########################################################
    def processPip(wav_dir,wav_save_dir,png_save_dir, split_wav = True):


        print('starting full conversion') # log


        print('SPLITTING\n')
        if (split_wav):
            WavPipeline.split(wav_dir, wav_save_dir)



        listwavs = os.listdir(wav_save_dir)
        totalwavs = len(glob.glob1(wav_save_dir, '*.wav'))
        i=1

        try:
            for splitwav in listwavs:
                if splitwav.endswith('.wav'):
            
                    ### report progress
                    print('(%d/%d)' % (i, totalwavs))

                    wavname = os.path.join(wav_save_dir, splitwav)              # .wav file with full path
                    fname = splitwav[:splitwav.rfind('.')]                      # remove .wav extension
                    scalname = os.path.join(png_save_dir, '%s.scal' % fname)    # .scal file with full path
                    scalgzname = scalname + '.gz'                               # .scal.gz file
                    mp3name = os.path.join(wav_save_dir, fname + '.mp3')        # .mp3 name
                                        
                    print('wavname: %s\nfname: %s\nscalname: %s\nscalgzname: %s\nmp3name: %s' % (wavname, fname, scalname, scalgzname, mp3name)) 


                    print('WAV TO SCL\n')
                    WavPipeline.wavToScl(wavname, scalname, scalgzname, mp3name)
                    print('SCL TO PNG\n')
                    WavPipeline.scalToPng(fname,scalname,scalgzname, png_save_dir)
                    print('PNG FLOOD FILL\n')
                    WavPipeline.flood_png(fname, png_save_dir)

                    i+=1

        except:
            print('################## ERROR DURING DATA PROCESSING ################')
            exit(-1)


    ####################
    ### wav --> scal ###
    ####################
    def wavToScl(wavname,scalname,scalgzname,mp3name):
        
        print('\n#####starting wav -> scal transformation')

        ### check for already existing .scal file
        if os.path.exists(scalname) or os.path.exists(scalgzname):
            print("SCAL file or gz %s already exists" % scalname)

        else:
            ################################################################
            ### create the scal file
            print("Creating SCAL file from \"" + wavname + "\".")
            scal = Scalogram(wavname)
            scal.write_to_file(filename=scalname)
            print("   ", scal)
            print('scalfile created') # log
   

            ################################################################
            ### compress .wav file once converted to .scal file
            print('compressing wav file %s' % wavname)
            print('compressing wav file %s' % wavname) # log
            os.system('ffmpeg -i %s %s' % (wavname, mp3name))
            print('wav -> mp3 compression complete')
            print('wav -> mp3 compression complete') # log


    ####################
    ### scal --> png ###
    ####################
    def scalToPng(fname,scalname,scalgzname, png_save_dir):

        print('STARTING SCL TO PNG')

        pngname = os.path.join(png_save_dir, '%s.png' % fname)  # .png file with full path

        print('\n##### starting scal -> png transformation')
        print(pngname)


        ### check for already existing .png file
        if os.path.exists(pngname):
            print("PNG file %s already exists" % pngname)
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
            print("Info on SCAL file \"" +sname+ "\":")
            scal = Scalogram(sname)
            print('loaded scal')
            # print("   ", scal)
            #argmax = scal.argmax()
            #argmin = scal.argmin()
            #print("   max:", scal[argmax[0]][argmax[1]], "(t:", argmax[0], ", f:", argmax[1], ")")
            #print("   min:", scal[argmin[0]][argmin[1]], "(t:", argmin[0], ", f:", argmin[1], ")")
            #print("   mean:", scal.mean())
            scal.write_to_png(filename=pngname)
            
            print('created pngfile')


    #################
    ### flood png ###
    #################
    def flood_png(fname, png_save_dir):

        pngname = os.path.join(png_save_dir, '%s.png' % fname)

        flood_dir = os.path.join(png_save_dir, 'flood')
        # create flooded png directory if doesn't exist
        if not os.path.isdir(flood_dir):
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
            png.write_to_png(filename=floodpngname);
            print('wrote')


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

#WavPipeline.processPip(wav_dir,wav_save_dir,png_save_dir)
"""