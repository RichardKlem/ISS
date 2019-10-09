import matplotlib.pyplot as plt
from scipy import signal, fftpack
from scipy.signal import butter
import numpy as np

t = np.linspace(-1, 1, 201)
x = (np.cos(2*np.pi*t) - np.sin(2*np.pi*t))
xn = x + np.random.randn(len(t)) * 0.2

b, a = butter(3, 0.05)

zi = signal.lfilter_zi(b, a)
z, _ = signal.lfilter(b, a, xn, zi=zi*xn[0])

z2, _ = signal.lfilter(b, a, z, zi=zi*z[0])
y = signal.filtfilt(b, a, xn)

plt.figure()
plt.plot(t, xn, 'b', alpha=0.75)
plt.plot(t, z, 'r--', t, z2, 'r', t, y, 'k')
plt.legend(('noisy signal', 'lfilter, once', 'lfilter, twice',
            'filtfilt'), loc='best')
plt.grid(True)
plt.show()

"""
x_fft = fftpack.fft(xn)
y_fft = fftpack.fft(y)
plt.plot(t, x_fft)
plt.grid(True)
plt.show()
plt.plot(t, y_fft)
plt.grid(True)
plt.show()
"""