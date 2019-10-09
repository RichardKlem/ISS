import matplotlib.pyplot as plt
from scipy import signal
import numpy as np

t = np.linspace(-1, 1, 128)  # vzorky pro h
x = np.repeat([0., 1., 0., 0.5], 256)  # signál
x = x + np.random.randn(len(x)) * 0.05  # přídání šumu
h = np.sin(np.pi * t / 2) + 1  # konvoluční funkce např. cos(np.pi * t) + 1

filtered = signal.convolve(x, h, mode='same') / sum(h)

fig, (ax_orig, ax_win, ax_filt) = plt.subplots(3, 1, sharex=True)
ax_orig.plot(x)
ax_orig.set_title('Original pulse')

ax_win.plot(h)
ax_win.set_title('Filter impulse response')

ax_filt.plot(filtered)
ax_filt.set_title('Filtered signal')

fig.show()
