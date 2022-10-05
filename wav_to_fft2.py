from scipy.io import wavfile as wav
from scipy.fftpack import fft
import numpy as np

rate, data = wav.read('/Users/Barbara/Downloads/eas.wav')
fft_out = fft(data)
print("done")
