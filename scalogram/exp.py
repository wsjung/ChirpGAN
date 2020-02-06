# JUST ME PLAYING AROUND

import pywt
import numpy as np
import matplotlib.pyplot as plt
import sys

TAU = 2*np.pi
SAMPLING_RATE = 300*1000
SAMPLING_PERIOD = 1/SAMPLING_RATE
SIGNAL_FREQ = 80*1000
AMPLITUDE = 1
VOICES_PER_OCTAVE = 64
BASE_SCALE = 133.125 # WHY?

wavelet = pywt.ContinuousWavelet('cmor5-60000')

# make data of a 2-kHz signal over 1 second, sampling rate of 100 kHz

np.set_printoptions(threshold=sys.maxsize)

# create 1 s of data at the given frequency sampling rate
x = np.arange(SAMPLING_RATE)
signal = AMPLITUDE * np.sin(TAU * x / (SAMPLING_RATE/SIGNAL_FREQ))
print(signal.shape)
print(signal[0:128])
# plot the signal
#fig,ax = plt.subplots(figsize=(50,10))
#ax.plot(x,signal)

scales = np.geomspace(BASE_SCALE*2, BASE_SCALE/2, VOICES_PER_OCTAVE*2+1)

coef, freqs=pywt.cwt(signal, scales, wavelet, SAMPLING_PERIOD) # data, scales, wavelet, period
mags = np.abs(coef)
print(freqs[len(freqs)//2])
if (freqs[len(freqs)//2]) != (60*1000): print("Problem!", file=sys.stderr)

print(freqs)
print(freqs.shape)
print(mags.shape)


fig, ax = plt.subplots(figsize=(12,12))
ax.invert_yaxis()
ax.imshow(mags, interpolation='nearest', cmap='gray', aspect='auto' )
plt.show()
