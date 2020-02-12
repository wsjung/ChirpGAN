# Copyright 2017 Adam A. Smith

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import numpy as np
import sys
import math
from struct import pack, unpack
from PIL import Image
import random

################################################################################
# THE SCALOGRAM OBJECT, THAT HOLDS A WAVELET TRANSFORM OF A WAV FILE
################################################################################
    
class Scalogram:
    """A class to hold the results of a wavelet transform"""

    # constants
    BANDWIDTH_FREQ = 100

    def __init__(self, source, name = None):
        """Create a new Scalogram object from a WAV or SCAL file, or copy another Scalogram."""
        if type(source) == str:
            # open up a WAV file, make a new scalogram
            if source.lower().endswith(".wav"):
                wav_data = Scalogram.extract_wav_data(source)

                scal_data = Scalogram.do_transform(wav_data[1], wav_data[0], 2000, 1000, 3)

                self.quality = 2000
                self.freqs = scal_data[0]
                self.data = scal_data[1]

                # name from given name, or the WAV's file name
                if name == None: self.name = source[:-4]
                else: self.name = name

            # loading up a scalogram directly from file
            elif source.lower().endswith(".scal"):

                # get the name
                if name == None: self.name = source[:-5]
                else: self.name = name

                # get the data
                in_stream = open(source, "rb")
                self.quality = int.from_bytes(in_stream.read(4), byteorder="little", signed=False)
                num_freqs = int.from_bytes(in_stream.read(4), byteorder="little", signed=False)

                self.freqs = np.fromfile(in_stream, "<f8", num_freqs)
                self.data = np.fromfile(in_stream, "<f8")
                self.data = self.data.reshape((int(len(self.data)/num_freqs), num_freqs))
            
                in_stream.close()

            else:
                raise TypeError("Cannot generate Scalogram from file \"" +source+ "\" of unknown type.")

        # given another Scalogram--make a copy
        elif type(source) == Scalogram:
            if name == None: self.name = source.name
            else: self.name = name
            self.quality = source.quality
            self.freqs = np.copy(source.freqs)
            self.data = np.copy(source.data)
            
        # final else--we didn't even get a string
        else:
            raise ValueError("Cannot make scalogram: source must be a file name!")
            
    ############################################################################
    # BASIC UTILITIES
    ############################################################################
            
    def get_freq(self, index):
        """Gets one of the frequencies."""
        return self.freqs[index]

    def get_freqs(self):
        """Returns a copy of the array of frequencies."""
        return self.freqs.copy()

    def max(self):
        """Gets the maximum value in this Scalogram."""
        return np.max(self.data)

    def min(self):
        """Gets the maximum value in this Scalogram."""
        return np.min(self.data)

    def argmax(self):
        """Where is the maximum value?"""
        index = np.argmax(self.data)
        return (index // self.get_num_freqs(), index % self.get_num_freqs())
    
    def argmin(self):
        """Where is the maximum value?"""
        index = np.argmin(self.data)
        return (index // self.get_num_freqs(), index % self.get_num_freqs())
    
    def mean(self):
        """Calculates the mean value in this Scalogram."""
        return np.mean(self.data)

    def get_num_freqs(self):
        """Return the number of frequencies contained."""
        return len(self.freqs)
            
    def get_num_times(self):
        """Return the number of time steps contained."""
        return len(self.data)

    def set_name(self, new_name):
        """Change the name to something else"""
        self.name = new_name

    def get_name(self):
        """Get the name of this Scalogram."""
        return self.name

    def get_flat_neighborhood(self, time, freq, max_distance = 3):
        """Return a 1D array of the time/freq pairs around the given time & frequency."""
        return self.get_neighborhood(time, freq, max_distance).flatten()

    def get_neighborhood(self, time, freq, max_distance = 3):
        """Return a 2D array of the time/freq pairs around the given time & frequency."""
        
        # if the "time" is a tuple, use that for time & freq, and turn max_distance into whatever freq holds
        if type(time) == tuple:
            max_distance = freq
            freq = time[1]
            time = time[0]

        # define the time & frequency ranges we need
        t_range = range(time - max_distance, time + max_distance + 1)
        f_range = range(freq - max_distance, freq + max_distance + 1)

        # easy, common case--everything has sufficient padding from outside
        if time >= max_distance and time < self.get_num_times() - max_distance and freq >= max_distance and freq < self.get_num_freqs() - max_distance:
            return self.data[t_range][:,f_range]

        # rarely, we'll need to go off the data's range--use Scalogram's least value
        # 1st, find the min value if we haven't already
        try: self.min_value
        except AttributeError: self.min_value = np.min(self.data)

        # 2nd, actually copy over (using min_value when off the edge)
        neighborhood = np.zeros((2*max_distance+1, 2*max_distance+1))
        for t in t_range:
            nt = t - (time - max_distance)
            if t < 0 or t >= self.get_num_times():
                neighborhood[nt].fill(self.min_value)
            else:
                for f in f_range:
                    nf = f - (freq - max_distance)
                    if f < 0 or f >= self.get_num_freqs(): neighborhood[nt][nf] = self.min_value
                    else: neighborhood[nt][nf] = self.data[t][f]

        return neighborhood        
    
    def __getitem__(self, key):
        """Allows us to use the values in a Scalogram like it's a 2D array."""
        return self.data[key]

    def __str__(self):
        """Return a string that summarizes the Scalogram's properties."""
        duration = str(self.get_num_times() / self.quality) + " s"
        rate =  "%g kHz" % (self.quality/1000)
        range = "range %g kHz-%g kHz" % ((self.freqs[0]/1000), (self.freqs[-1]/1000))
        num_octaves = math.log(self.freqs[-1] / self.freqs[0], 2)
        voices_per_octave = "%g VpO" % ((self.get_num_freqs()-1) / num_octaves)
        
        return "<Scalogram \"" +self.name+ "\": " +duration+ ", " +rate+ ", " +range+ ", " +voices_per_octave+ ">"

    def clone(self):
        """Create an independent duplicate of this Scalogram."""
        return Scalogram(self)
    
    ############################################################################
    # FILE WRITING
    ############################################################################
    
    def write_to_file(self, filename = None):
        """Writes out a ".scal" file that contains this Scalogram."""

        # if no file name given, base it off the internally-stored name
        if filename == None:
            filename = self.name + ".scal"
            #print("using default filename: " +filename)

        # actually write to file, forcing little-endian encoding for everything
        out_stream = open(filename, "wb")

        # first quality & number of freqs, as unsigned 4-byte ints
        out_stream.write((self.quality).to_bytes(4, byteorder="little", signed=False))
        out_stream.write((len(self.freqs)).to_bytes(4, byteorder="little", signed=False))

        # then the freqs array and the amplitudes themselves, as little-endian doubles
        if sys.byteorder == "little":
            self.freqs.tofile(out_stream)
            self.data.tofile(out_stream)
        else:
            for f in self.freqs: out_stream.write(pack("<d", f))
            for row in self.data:
                for d in row: out_stream.write(pack("<d", d)) 
        out_stream.close()

    def write_to_png(self, scale=(0.0,1.0), filename = None):
        """Output a PNG of the Scalogram"""
        from scipy.misc import toimage
        #from PIL.Image import fromarray
        data = np.flipud(np.transpose(self.data)) # transpose & flip vertical

        if filename == None: filename = self.name + ".png"

        # no scale--autoscale the sucker
        if scale == None:
            im = toimage(-data)
            #im = fromarray(-data, mode='L')
            im.save(filename)

        # there is a scale--use it
        else:
            im = toimage(scale[1] - data)
            #im = fromarray(scale[1] - data, mode='L')
            im.save(filename, cmin=scale[0], cmax=scale[1])


    ############################################################################
    # SOUND & WAVELET STUFF
    ############################################################################
    
    @staticmethod
    def extract_wav_data(filename):
        """Opens a WAV file, returning a tuple of the quality (sample rate) and the data itself."""

        try:
            import wave
        except ImportError:
            print("Sorry, you need the Python wave module to work with .wav files.", file=sys.stderr)
            sys.exit(1)
        
        # set up & open file
        w = wave.open(filename)
        num_frames = w.getnframes()
        width = w.getsampwidth()
        quality = w.getframerate()
        data = np.empty(num_frames)

        # for 1-byte frames, we need values from 0 to 255
        if width == 1:
            for i in range(num_frames):
                frame = w.readframes(1)
                frame_int = int.from_bytes(frame)
                data[i] = frame_int

        # for 2-byte frames (and maybe others) we have signed values
        else:
            for i in range(num_frames):
                frame = w.readframes(1)
                frame_int = int.from_bytes(frame, byteorder='little', signed=True)
                data[i] = frame_int

        # close file & return the array
        w.close()
        return (quality, data)

    @staticmethod
    def do_transform(data, quality=44100, scalogram_quality = 2000, base_freq = 30000, num_octaves = 2, voices_per_octave = 64):
        # figure out frequencies to test for
        central_freq = base_freq * (2**(num_octaves/2))
        freqs = np.geomspace(base_freq, base_freq * (2**num_octaves), num=num_octaves*voices_per_octave+1, endpoint=True)

        # allocation
        resampling_factor = int(quality / scalogram_quality)
        mags = np.empty((int(len(data) * scalogram_quality / quality), len(freqs)))

        # do each individual frequency, 1 at a time
        for f in range(len(freqs)):
            scale = central_freq / freqs[f]
            wavelet = Scalogram.make_wavelet(quality, central_freq, 0.000001, scale)
            #print(len(wavelet))
            convolution = np.abs(np.convolve(data, wavelet, mode="same"))

            for t in range(len(mags)):
                mags[t][f] = (abs(convolution[t*resampling_factor : (t+1)*resampling_factor])).mean()

        return (freqs, mags)

#    def do_new_transform(data, quality=44100, scalogram_quality = 2000, base_freq = 30000, num_octaves = 2, voices_per_octave = 50):
#        print(len(data), data)
#        freqs = np.geomspace(base_freq, base_freq * (2**num_octaves), num=num_octaves*voices_per_octave+1, endpoint=True)
#        mags = np.empty((int(len(data) * scalogram_quality / quality), len(freqs)))
#        factor = int(quality / scalogram_quality)
#
#        center_freq = base_freq*(2**(num_octaves/2))  # put the center freq in the middle of the expected range
#        scales = freqs / center_freq
#        print("cf:", center_freq)
#        print("quality:", quality)
#        print(freqs, scales)
#
#        for i in range(len(freqs)):
#            wavelet = Scalogram.make_wavelet(quality, freqs[i], 0.000001, scales[i])
#            con = np.abs(np.convolve(data, wavelet))
#            for t in range(len(mags)):
#                mags[t][i] = (abs(con[t*factor : (t+1)*factor])).mean()
#            print(i, len(wavelet))
#
#        return (freqs, mags)

    #Scalogram.TAU = 2.0*np.pi
    #Scalogram.I = 0+1j
    #Scalogram.ITAU = TAU * I

    @staticmethod
    def make_wavelet(quality, frequency, bandwidth, scaling = 1.0):
        """Make a complex Morlet wavelet"""
        itau = 2.0 * np.pi * (0+1j)
        # determine width from bandwidth
        stdev = np.sqrt(bandwidth/2)
        limit = int(np.ceil(stdev * 3 * quality * scaling)) # out to 3 stdevs
        wavelet = np.empty((2*limit+1), dtype=complex)
        z = len(wavelet)//2

        # loop thru every element in half the wavelet
        coefficient = 1.0 / (np.sqrt(np.pi * bandwidth))
        for i in range(z+1):
            t = i / quality / scaling 

            sinusoid = np.exp(t * itau * frequency)
            gaussian = np.exp(-t*t/bandwidth)
            wavelet[z+i] = sinusoid * gaussian
            wavelet[z-i] = wavelet[z+i].conjugate() # complex conjugate for other half

        return wavelet
    
#    @staticmethod
#    def make_wavelet(quality, frequency, bandwidth, scaling = 1.0):
#        itau = 2.0 * np.pi * (0+1j)
#        # determine width from bandwidth
#        stdev = np.sqrt(bandwidth/2)
#        limit = int(np.ceil(stdev * 3 * quality / scaling)) # out to 3 stdevs
#        #print("limit:", limit)
#        wavelet = np.empty((2*limit+1), dtype=complex)
#        z = len(wavelet)//2
#
#        # loop thru every element in half the wavelet
#        coefficient = 1.0 / (np.sqrt(np.pi * bandwidth))
#        for i in range(z+1):
#            t = i / quality * scaling 
#
#            sinusoid = np.exp(t * itau * frequency)
#            gaussian = np.exp(-t*t/bandwidth)
#            wavelet[z+i] = sinusoid * gaussian
#            wavelet[z-i] = wavelet[z+i].conjugate() # complex conjugate for other half
#
#        return wavelet


    
    @staticmethod
    def do_pywt_transform(data, quality=44100, scalogram_quality = 2000, base_freq = 30000, num_octaves = 2, voices_per_octave = 50):
        """Actually perform the wavelet transform, using the PyWavelet module."""
        CORRECTION_FACTOR = 10000
        try:
            import pywt
        except ImportError:
            print("Sorry, you need the PyWavelets (\"pywt\") module to create scalograms.", file=sys.stderr)
            sys.exit(1)
        
        # workaround--the pywt has accuracy bugs when we get to high freqs, so slow everything down
        base_freq /= CORRECTION_FACTOR
        quality /= CORRECTION_FACTOR
        scalogram_quality /= CORRECTION_FACTOR
        
        # construct the wavelet we want
        wavelet = pywt.ContinuousWavelet('cmor')
        wavelet.bandwidth_frequency = Scalogram.BANDWIDTH_FREQ
        wavelet.center_frequency = base_freq*2 # put the center freq in the middle of the expected range

        base_scale = quality * wavelet.center_frequency / base_freq
        far_scale = base_scale / 2**num_octaves
        scales = np.geomspace(base_scale, far_scale, num=num_octaves*voices_per_octave+1, endpoint=True)

        #mags = np.empty((len(scales), int(len(data) * scalogram_quality / quality)))
        mags = np.empty((int(len(data) * scalogram_quality / quality), len(scales)))
        freqs = np.empty(len(scales))

        # do actual calculation 1 scale at a time, resampling the magnitudes (saves memory)
        factor = int(quality / scalogram_quality)
        for f in range(len(scales)):
            coeffs, freq = pywt.cwt(data, scales[f], wavelet, 1/quality)

            freqs[f] = freq[0] * CORRECTION_FACTOR
            for t in range(len(mags)):
                mags[t][f] = (abs(coeffs[0][t*factor : (t+1)*factor])).mean()

        return (freqs, mags)

    ############################################################################
    # NORMALIZATION
    ############################################################################

    def normalize(self, parameters=None):
        """Linearly normalize a single Scalogram to have mean 0.0, max 1.0. Or pass the tuple returned by another normalization, to normalize identically to that one. Returns a tuple to be used for future normalizations (mean and max-mean)."""
        return Scalogram.normalize_many((self,), parameters)
    
    @staticmethod
    def normalize_many(scals, parameters=None):
        """Uses a linear transform to adjust many Scalograms identically, so the global mean is 0.0 and the global max is 1.0. Or pass the tuple returned by another normalization, to normalize identically to that one. Returns a tuple to be used for future normalizations (mean and max-mean)."""

        # figure out the mean, subtract it everywhere
        if parameters: mean = parameters[0]
        else: mean = Scalogram.find_global_mean(scals)
        for scal in scals: np.subtract(scal.data, mean, out=scal.data)

        # now find the new max (max - mean), divide by it
        if parameters: diff = parameters[1]
        else:
            diff = scals[0][0][0]
            for scal in scals: diff = max(diff, scal.data.max())
        for scal in scals: np.divide(scal.data, diff, out=scal.data)

        # if there were old min values, remove them
        for scal in scals:
            try: del scal.min_value
            except AttributeError: pass

        # return what we did, for later use
        if parameters: return parameters
        else: return (mean, diff)

    def log_normalize(self, max_element=None):
        """Normalizes the data on a log scale, zeroing out all resulting negatives."""
        # find the max element if one isn't provided
        if max_element == None: max_element = self.data.max()
        log_max = math.log(max_element)
        
        # normalize the data based on a log scale (in place)
        np.fmax(self.data, 1.0, out=self.data) # min value of 1 (pre-log), avoids NaN nastiness
        np.log(self.data, out=self.data)
        np.divide(self.data, log_max, out=self.data)

        self.min_value = 0.0 # min value is now 0.0 (even if there is no actual 0.0)
        
        # return the max element, in case we want to normalize another Scalogram
        return max_element
        
    @staticmethod
    def log_normalize_many(scals, max_element=None):
        """Identically normalizes many Scalograms on a log scale, zeroing out all resulting negatives."""

        # if given no max element, find the max from among everything
        if max_element == None:
            max_element = scals[0][0][0]
            for scal in scals: max_element = max(max_element, scal.data.max())

        # now normalize each Scalogram to the same scale
        for scal in scals: scal.log_normalize(max_element)

        # return the max element, to normalize in the future
        return max_element

    @staticmethod
    def find_global_mean(scals):
        """Find the mean value of a bunch of Scalograms. Each time/frequency pair is weighted equally."""

        if len(scals) == 1: return scals[0].mean()

        means = np.empty((len(scals)))
        weights = np.empty((len(scals)))

        num_freqs = scals[0].get_num_freqs()
        for i in range(len(scals)):
            assert scals[i].get_num_freqs() == num_freqs # might need to implement variable freq sizes later
            means[i] = scals[i].mean()
            weights[i] = scals[i].get_num_times()
        return np.average(means, weights=weights)
    
    def normalize_neg1_to_1(self):
        """Normalize the Scalogram so that all entries are between -1.0 and 1.0 (linear transform)."""

        # find the min & max (and normalization denominator)
        min = np.min(self.data)
        max = np.max(self.data)
        denom = (max-min)/2

        # normalize everything (in place)
        np.subtract(self.data, min, out=self.data)
        np.divide(self.data, denom, out=self.data)
        np.subtract(self.data, 1.0, out=self.data) # doing subtract in 2 steps helps accuracy of floats

        # write over old minimum value, in case it exists
        self.min_value = -1.0
        
    ############################################################################
    # MISCELLANEOUS FUNCTIONS
    ############################################################################

    def display(self):
        """Uses Matlabplot to output a quick image of the Scalogram"""

        # make sure things are imported
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FormatStrFormatter

        data_to_show = np.transpose(self.data)
        plt.figure(figsize=(20,5))
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.1)
        ax = plt.gca()

        # figure possible x & y values
        num_times = self.get_num_times()
        x = np.linspace(0, num_times/self.quality, num_times+1)
        y = self.freqs/1000

        num_octaves = math.log(self.freqs[-1] / self.freqs[0], 2)
        ticks = np.arange(self.freqs[0]/1000, self.freqs[-1]/1000, 10)
        if ticks[-1] != self.freqs[-1]/1000: ticks = np.append(ticks, self.freqs[-1]/1000)
        
        ax.set_yscale("log")
        plt.axis([0, 0.2, ticks[0], ticks[-1]])
        ax.set_yticks(ticks)
        ax.set_xlabel("s")
        ax.set_ylabel("kHz")
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        ax.pcolormesh(x, y, data_to_show, cmap="Greys")

        plt.gcf().canvas.set_window_title(self.name)
        
        plt.show()        

    # DEPRECATED--use Tag constructor instead with Scalogram as source
    #def make_tag(self):
    #    return Tag((self.get_num_times(), self.get_num_freqs()), self.name)


################################################################################
# THE TAG OBJECT, HOLDING AN ARRAY OF BOOLEANS FOR CALL LOCATIONS
################################################################################
    
class Tag:
    """A class to hold the locations of calls"""

    def __init__(self, source, name=None):
        """Create a new Tag object from either a PNG or TAG file."""

        if type(source) == str:
            # open up a PNG file, instantiate the Tag
            if source.lower().endswith(".png"):
                img = Image.open(source)

                num_times = img.width
                num_freqs = img.height
                self.data = np.zeros((num_times, num_freqs), dtype=np.bool)

                # go thru pixel by pixel, setting t/f pair with non-0 alpha to True
                for t in range(num_times):
                    for f in range(num_freqs):
                        pixel = img.getpixel((t, (num_freqs-1)-f))
                        self.data[t][f] = pixel[-1] > 0

                # extract the Tag's name from the filename
                if name == None: self.name = source[:-4]
                else: self.name = name

                
            # loading up a Tag directly from file
            elif source.lower().endswith(".tag"):
                # open the file & read the data
                in_stream = open(source, "rb")
                num_times = int.from_bytes(in_stream.read(4), byteorder="little", signed=False)
                num_freqs = int.from_bytes(in_stream.read(4), byteorder="little", signed=False)
                flat_array = np.unpackbits(np.fromfile(in_stream, "uint8")).astype("bool")[:num_freqs*num_times]
                self.data = np.reshape(flat_array, (num_times, num_freqs))
                in_stream.close()

                # don't forget the name!
                if name == None: self.name = source[:-4]
                else: self.name = name

            # output (debugging)
            #print("#F: " + str(len(self.data)))
            #print("#T: " + str(len(self.data[0])))
            #print(self.data)
            #print(self.data.dtype)

        #elif type(source) == tuple:
        #    self.name = name
        #    if len(source) == 2: self.data = np.zeros(source, dtype=np.bool)
        #    else: raise ValueError("Tag must be 2-dimensional (not " +str(len(source))+ ")!")

        # new, empty Tag that matches a Scalogram's dimensions
        elif type(source) == Scalogram:
            if name == None: self.name = source.get_name()
            else: self.name = name
            self.data = np.zeros((source.get_num_times(), source.get_num_freqs()), dtype=np.bool)
            
        # given another Tag--make a copy
        elif type(source) == Tag:
            if name == None: self.name = source.name
            else: self.name = name
            self.data = np.copy(source.data)
            
        # final else--we didn't even get a string/tuple/Scalogram/Tag
        else:
            raise ValueError("Cannot make Tag: source must be a file name, Scalogram, or Tag!")

        # finally make a sorted list of tagged times
        self.recalc_tagged_times()

    def recalc_tagged_times(self):
        self.tagged_times = []
        for t in range(len(self.data)):
            if True in self.data[t]: self.tagged_times.append(t)
            
    ############################################################################
    # BASIC UTILITIES
    ############################################################################
            
    def print_array(self):
        print(self.data)

    def get_num_freqs(self):
        """Return the number of frequencies contained."""
        return len(self.data[0])
            
    def get_num_times(self):
        """Return the number of time steps contained."""
        return len(self.data)

    def get_num_tagged_times(self):
        """Return the number of times with tagged elements."""
        return len(self.tagged_times)

    def is_time_tagged(self, time):
        """Return True iff some frequency at this time is tagged. Logarithmic with respect to # tagged times in this Scalogram."""
        possible_index = np.searchsorted(self.tagged_times, time) # get some index back
        if possible_index >= len(self.tagged_times): return False # if time is beyond last tagged time, index will be too large
        return self.tagged_times[possible_index] == time # make sure that index actually holds this time

    def are_times_tagged(self):
        """Return T/F array indicating if each time is tagged"""
        bool_tagged_times = np.zeros(self.get_num_times(), dtype=np.bool)
        for t in self.tagged_times: bool_tagged_times[t] = True
        return bool_tagged_times
    
    def get_name(self):
        """Get the name of this Tag."""
        return self.name

    def __getitem__(self, key):
        """Allows us to use the values in a Tag like it's a 2D array."""
        return self.data[key]

    def __str__(self):
        """Return a string that summarizes the Tag's properties."""
        return "<Tag \"" +self.name+ "\": " +str(self.get_num_times())+ "t × " +str(self.get_num_freqs()) + "f>"
    
    def clone(self):
        """Create an independent duplicate of this Tag."""
        return Tag(self)
    
    ############################################################################
    # FILTERING OUT TAGS
    ############################################################################

    def filter_small_calls(self, minimum_size):
        if minimum_size <= 1: return
        known_points = set()
        for t in range(len(self.data)):
            for f in range(len(self.data[t])):
                if (t,f) in known_points: continue

                # extract a call at this point, stop now if there's no call
                call_set = self.extract_call_as_set(t,f)
                size = len(call_set)
                if size == 0: continue

                # call to known list, kill it if it isn't big enough
                known_points.update(call_set)
                #print("Found call of size", size, "at", (t,f))
                if size < minimum_size: self.erase_call(call_set)
        self.recalc_tagged_times()

    
    def extract_call_as_set(self, time, frequency):
        """Get this call as a set of points. (Return {} if no call.)"""
        if not self.data[time][frequency]: return frozenset()

        call_set = set()

        self.grab_column(call_set, time, frequency)
        return frozenset(call_set)
        

    def grab_column(self, call_set, time, frequency):
        # current point check
        if time < 0 or time >= self.get_num_times() or frequency < 0 or frequency >= self.get_num_freqs(): return
        if not self.data[time][frequency] or (time,frequency) in call_set: return
        
        # find min & max freqs of the call at this time
        min_f = max_f = frequency
        num_freqs = self.get_num_freqs()
        while min_f > 0 and self.data[time][min_f-1] and not (time,min_f-1) in call_set: min_f -= 1
        while max_f < num_freqs-1 and self.data[time][max_f+1] and not (time,max_f+1) in call_set: max_f += 1

        # now add the pixels to the call set
        for f in range(min_f, max_f+1): call_set.add((time, f))

        # and recurse
        num_times = self.get_num_times()
        for f in range(min_f, max_f+1):
            #if time > 0 and f > 0 and self.data[time-1][f-1] and not (time-1,f-1) in call_set:
            self.grab_column(call_set, time-1, f-1)
            self.grab_column(call_set, time-1, f)
            self.grab_column(call_set, time-1, f+1)

            self.grab_column(call_set, time+1, f-1)
            self.grab_column(call_set, time+1, f)
            self.grab_column(call_set, time+1, f+1)
            #if time > 0 and self.data[time-1][f] and not (time-1,f) in call_set: self.grab_column(call_set, time-1, f)
            #if time > 0 and f < num_times-1 and self.data[time-1][f+1] and not (time-1,f+1) in call_set: self.grab_column(call_set, time-1, f-1)

            #if time > 0 and self.data[time-1][f] and not (time-1,f) in call_set: self.grab_column(call_set, time-1, f)
            #if time < num_times-1 and self.data[time+1][f] and not (time+1,f) in call_set: self.grab_column(call_set, time+1, f)

        return call_set

    def erase_call(self, call_set):
        """Take some call and totally remove it from the Tag."""
        for d in call_set:
            self.data[d[0]][d[1]] = False
        
    ############################################################################
    # GRABBING RANDOM TAGGED TIME/FREQ PAIRS
    ############################################################################
    
    def get_random_tagged_point(self):
        """Grab some tagged time/freq pair at random from this Tag"""

        if len(self.tagged_times) == 0: return None
        time = random.choice(self.tagged_times)

        # given the time, find a tagged freq
        max = np.sum(self.data[time])
        rand = random.randrange(max)
        for f in range(len(self.data[time])):
            if self.data[time][f]:
                if rand == 0: return (time,f)
                else: rand -= 1

        # this should never be reached--blow up if it does
        raise RuntimeError("Random selection went beyond allowed frequencies.")
        
    def get_random_near_tagged_point(self, halo_size):
        """Grab some tagged time/freq pair at random from this Tag"""

        if len(self.tagged_times) == 0: return None
        time = random.choice(self.tagged_times)

        # given the time, create a set of freqs near tagged ones, that aren't tagged
        near_set = set()
        num_freqs = self.get_num_freqs()
        for f in range(num_freqs):
            if self.data[time][f]:
                for n in range(max(0,f-halo_size), min(num_freqs, f+halo_size+1)):
                    if not self.data[time][n]: near_set.add(n)

        # okay, grab the freq and return
        freq = random.sample(near_set, 1)[0]
        return (time, freq)

    ############################################################################
    # FILE WRITING
    ############################################################################
    
    def write_to_file(self, filename = None):
        """Writes out a ".tag" file that contains this Tag."""

        # if no file name given, base it off the internally-stored name
        if filename == None: filename = self.name + ".tag"

        # actually write to file, forcing little-endian encoding for everything
        out_stream = open(filename, "wb")

        # first number of freqs & number of times, as unsigned 4-byte ints
        out_stream.write((len(self.data)).to_bytes(4, byteorder="little", signed=False))
        out_stream.write((len(self.data[0])).to_bytes(4, byteorder="little", signed=False))

        # then flatten & pack the data & write it (since it's bytes, no endianess issues)
        packed = np.packbits(self.data)
        packed.tofile(out_stream)

        out_stream.close()

    def write_to_png(self, filename = None, color = "red"):
        """Output a PNG of the Tag"""

        # figure out the color
        if type(color) == str: color = Tag.get_tuple_from_color(color)
        elif type(color) == int: color = (color, color, color, 255)
        elif type(color) == float: color = (int(color*255), int(color*255), int(color*255), 255)
        elif len(color) == 3: color = (color[0], color[1], color[2], 255)
        elif len(color) == 1: color = (color[0], color[0], color[0], 255)
        
        # make new Image
        num_times = self.get_num_times()
        num_freqs = self.get_num_freqs()
        img = Image.new("RGBA", (num_times, num_freqs))
        pixels = img.load()

        # go thru pixel by pixel
        for t in range(num_times):
            for f in range(num_freqs):
                if self.data[t][f]: pixels[t, (num_freqs-1)-f] = color
        
        if filename == None: filename = self.name + ".tag.png"
        img.save(filename)

    ############################################################################
    # THESE ARE STATIC METHODS TO GET RANDOM TRAINING POINTS
    ############################################################################

    @staticmethod
    def get_training_point_batch(batch_size, tags, bad_tags = None, types={"call", "nearcall", "fakecall", "random"}):
        """Get a list of training points to train a NN, based on tags and bad_tags."""
        batch = []
        for _ in range(batch_size):
            batch.append(Tag.get_training_point(tags, bad_tags, types))

        return batch
    
    @staticmethod
    def get_training_point(tags, bad_tags = None, types={"call", "nearcall", "fakecall", "random"}):
        """Get a single training point to train a NN, based on tags and bad_tags."""

        # first figure out which type we need, randomly (ensuring consistency with passed args)
        if type(types) == str: types = {types}
        if bad_tags == None: types.discard("fakecall")
        point_type = random.sample(types, 1)[0]

        # actually get the point
        if point_type == "call": return Tag.get_tagged_training_point(tags)
        if point_type == "nearcall": return Tag.get_near_tagged_training_point(tags)
        if point_type == "fakecall": return Tag.get_tagged_training_point(bad_tags)
        if point_type == "random": return Tag.get_random_training_point(tags)
        raise ValueError("Unknown point type: " +str(point_type))

    @staticmethod
    def get_tagged_training_point(tags):
        """Returns a (tag#, time#, call#) that is tagged; used for either call training points or fake call training points"""
        tag_index = Tag.choose_tag_index_randomly(tags)

        pair = tags[tag_index].get_random_tagged_point()
        return (tag_index, pair[0], pair[1])
            
    @staticmethod
    def get_near_tagged_training_point(tags, halo_size = 3):
        """Returns a (tag#, time#, call#) that is tagged; used for either call training points or fake call training points"""
        tag_index = Tag.choose_tag_index_randomly(tags)

        pair = tags[tag_index].get_random_near_tagged_point(halo_size)
        return (tag_index, pair[0], pair[1])

    @staticmethod
    def choose_tag_index_randomly(tags):
        """Returns a tag #, weighted by the number of tagged times."""
        # count the number of tagged times
        num_tagged_times = 0
        for tag in tags: num_tagged_times += tag.get_num_tagged_times()
        time_index = random.randrange(num_tagged_times)

        # determine which Tag to use
        tag_index = 0
        while time_index >= tags[tag_index].get_num_tagged_times():
            time_index -= tags[tag_index].get_num_tagged_times()
            tag_index += 1

        return tag_index
                        
    @staticmethod
    def get_random_training_point(tags_or_scalograms):
        """Returns a random (tag#, time#, call#) tuple from the passed tags or scalograms."""

        # determine a random time from all the Tags/Scalograms
        num_times = 0
        for tag in tags_or_scalograms: num_times += tag.get_num_times()
        time_index = random.randrange(num_times)

        # place it properly within a Tag
        tag_index = 0
        while time_index >= tags_or_scalograms[tag_index].get_num_times():
            time_index -= tags_or_scalograms[tag_index].get_num_times()
            tag_index += 1

        # and supplement it with a random freq
        freq_index = random.randrange(tags_or_scalograms[tag_index].get_num_freqs())

        return (tag_index, time_index, freq_index)

    ############################################################################
    # PRECISION/RECALL STUFF
    ############################################################################
    
    def calc_precision_recall(self, gold_standard):
        """Calc the precision, recall, and F1 score of a Tag vs. some gold standard."""
        posnegs = self.calc_posnegs(gold_standard)
        return Tag.calc_precision_recall_from_posnegs(posnegs)

    def calc_timewise_precision_recall(self, gold_standard):
        """Calc the precision, recall, and F1 score of a Tag vs. some gold standard, considering only times as being +/-."""
        posnegs = self.calc_timewise_posnegs(gold_standard)
        return Tag.calc_precision_recall_from_posnegs(posnegs)
    
    @staticmethod
    # posnegs is (TP, FP, TN, FN)
    def calc_precision_recall_from_posnegs(posnegs):
        """Calc the precision, recall, and F1 score, given true/false positives and negatives."""

        # no true positives--things might be weird
        if posnegs[0] == 0:
            precision = recall = f1_score = 0 # if P = R = 0, lim(F1) as P,R -> 0 is 0, so just make it 0
            if posnegs[1] == 0: precision = f1_score = np.NaN # TP=FP=0, so precision undefined
            if posnegs[3] == 0: recall = f1_score = np.NaN # TP=FN=0, so recall undefined

        # almost always, this one will trigger
        else:
            precision = posnegs[0] / (posnegs[0] + posnegs[1]) # TP / (TP + FP)
            recall = posnegs[0] / (posnegs[0] + posnegs[3]) # TP / (TP + FN)
            f1_score = 2 * (precision * recall) / (precision + recall) # harmonic mean

        return (precision, recall, f1_score)
        
    def calc_posnegs(self, gold_standard):
        """Calculate true/false positives and true/false negatives vs. some gold standard."""

        # make sure we have a good standard
        if type(gold_standard) == str:
            gold_standard = Tag(gold_standard)

        if type(gold_standard) != Tag:
            raise ValueError("Unknown standard: " +str(gold_standard))

        if len(self.data) != len(gold_standard.data) or len(self.data[0]) != len(gold_standard.data[0]):
            raise ValueError("Mismatch in gold standard's size")

        # add up true/false positives & negatives
        true_pos = true_neg = false_pos = false_neg = 0
        for t in range(len(self.data)):
            for f in range(len(self.data[t])):
                if self.data[t][f] and gold_standard.data[t][f]: true_pos += 1
                elif self.data[t][f] and not gold_standard.data[t][f]: false_pos += 1
                elif not self.data[t][f] and gold_standard.data[t][f]: false_neg += 1
                else: true_neg += 1

        return (true_pos, false_pos, true_neg, false_neg)

    def calc_timewise_posnegs(self, gold_standard):
        """Calculate true/false positives and true/false negatives vs. some gold standard, with respect to times only."""

        # make sure we have a good standard
        if type(gold_standard) == str:
            gold_standard = Tag(gold_standard)

        if type(gold_standard) != Tag:
            raise ValueError("Unknown standard: " +str(gold_standard))

        if len(self.data) != len(gold_standard.data) or len(self.data[0]) != len(gold_standard.data[0]):
            raise ValueError("Mismatch in gold standard's size")

        # add up true/false positives & negatives
        true_pos = true_neg = false_pos = false_neg = 0
        self_times = self.are_times_tagged()
        gold_times = gold_standard.are_times_tagged()

        for t in range(len(self_times)):
            if self_times[t] and gold_times[t]: true_pos += 1
            elif self_times[t] and not gold_times[t]: false_pos += 1
            elif not self_times[t] and gold_times[t]: false_neg += 1
            else: true_neg += 1

        return (true_pos, false_pos, true_neg, false_neg)

    ############################################################################
    # MISCELLANEOUS STATIC HELPER METHODS
    ############################################################################
    
    @staticmethod
    def get_tuple_from_color(color):
        if color.lower() == "red": return (255, 0, 0, 255)
        elif color.lower() == "orange": return (255, 128, 0, 255)
        elif color.lower() == "yellow": return (255, 255, 0, 255)
        elif color.lower() == "green": return (0, 153, 51, 255)
        elif color.lower() == "blue": return (0, 51, 204, 255)
        elif color.lower() == "purple": return (153, 0, 153, 255)
        elif color.lower() == "black": return (0, 0, 0, 255)
        elif color.lower() == "white": return (255, 255, 255, 255)
        elif color.lower() == "gray" or color.lower() == "grey": return (128, 128, 128, 255)

    @staticmethod
    def get_corresponding_tags_by_name(scalograms, pre_extension = ""):
        """Given a bunch of scalograms, use their name to find corresponding .tag files"""
        if type(scalograms) == Scalogram:
            filename = scalograms.get_name() + pre_extension + ".tag"
            return Tag(filename)

        tags = []
        for scal in scalograms:
            filename = scal.get_name() + pre_extension + ".tag"
            tags.append(Tag(filename))
        return tags

