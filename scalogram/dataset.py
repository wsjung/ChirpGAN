import os
import numpy as np
from PIL import Image

class Dataset:

    def __init__(self, data_dir):
        dataset_save_dir = os.path.join(data_dir, "..")

        scal = self.load_scal(data_dir)

        std_scal = self.standardize(scal)

        calls = np.array([self.extract_calls(s, 600) for s in std_scal])

        filename = os.path.join(dataset_save_dir, "dataset.npz")

        np.savez(filename, calls)
        print('dataset saved: ', filename)

    # load scalograms from directory
    def load_scal(self, data_dir):
        images = []
        # append images to list
        for filename in sorted(os.listdir(data_dir)):
            img = Image.open(os.path.join(data_dir, filename))
            images.append(img)
            print(filename)
        
        # convert images to np array
        scal = [np.array(img) for img in images]
        
        return scal

    # type cast to float32
    # standardize to mean +- 3 std and clip
    def standardize(self, scalograms):
        #scalograms = [(s.astype(np.float32) - 127.5)/127.5 for s in scalograms]
        scalograms = [s.astype(np.float32) for s in scalograms] # type cast to np.float32
        scalograms = [(s - np.mean(s)) / np.std(s) for s in scalograms] # standardize
        scalograms = [np.clip(s, np.mean(s) - 3*np.std(s), np.mean(s) + 3*np.std(s)) for s in scalograms] # clip 
        
        # for s in scalograms:
        #     print('min: %f, max: %f, mean: %f, std: %f' % (np.min(s), np.max(s), np.mean(s), np.std(s)))
            
        #norm = plt.Normalize(-1,1) # normalization for pyplot    
            
        return scalograms

    def silent(self, m, arr):
        return np.all(np.isclose(arr, m))

    def extract_calls(self, scal, width):
        m = np.min(scal)
        
        calls = []
        
        start = -1
        end = -1
        
        inCall = False
        
        for x in range(1,scal.shape[1]):
            if self.silent(m, scal[:,x]): # x silent
                if self.silent(m, scal[:,x-1]): # x-1 silent
                    if inCall:
                        if x - start >= width:
                            calls.append([start,end])
                            inCall = False
                            start = x - 1
                else: # x-1 not silent
                    end = x
            else: # x not silent
                if self.silent(m, scal[:,x-1]): # x-1 silent
                    if not inCall:
                        start = x - 1
                        inCall = True
                else: # x-1 not silent
                    if x - start >= width:
                        calls.append([start,x])
                        start = x - 1                
                        
        return calls
