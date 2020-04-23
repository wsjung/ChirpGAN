import sys
import os

DURATION = 130
SAVE_DIR = 'split_wavs'
WAV_DIR = 'wavefiles'

class DataSplitter:

    def __init__(self, duration, wav_dir, save_dir):
        
        self.split(duration, wav_dir, save_dir)
    
    def split(self, duration, wav_dir, save_dir):

        # # wrong usage
        # if len(wav_dir) < 1:
        #     # command = sys.argv[0]
        #     # print("Usage: python %s <wav-directory-1> <wav-directory-2> ..." % command, file=sys.stderr)
        #     print("## Directory not specified... Aborting")
        #     exit(-1)
        
        # verify directory integrity
        if not os.path.isdir(wav_dir): 
            print("Error: \"%s\" is not a directory" % wav_dir, file=sys.stderr)
            exit(-1)
        
        # list files
        print('List of files in %s:' % wav_dir)
        os.system('ls -l %s' % wav_dir)
    

        # ffmpeg 130 seconds for each wav file in directory
        for f in os.listdir(wav_dir):
            if f.endswith('.wav'):
                print('Splicing wav file: %s' % f)

                fwav = os.path.join(wav_dir, f)
                fname = f[:-4] # filename without extension

                os.system('ffmpeg -i %s -f segment -segment_time %d -c copy ./%s/%s%%01d.wav' % (fwav, duration, save_dir, fname))

                print('compressing wav file')
                os.system('ffmpeg -i %s %s.mp3' % (fwav, os.path.join(wav_dir, fname)))
                #print('deleting wav file')
                #os.system('rm %s' % fwav)


        # print('### DONE ###')

if __name__ == '__main__':
    datasplitter = DataSplitter(DURATION, WAV_DIR, SAVE_DIR)
