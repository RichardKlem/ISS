import matplotlib.pyplot as plt
from scipy import signal
import numpy as np

"""
Napriklad:
    vstupni signal x = [0, 0, 1, 1, 0, 0]
    filtr = 0.5 * x[n] + 0.5 * x[n-1]
    filtru odpovida impulsni odezva h = [0.5 0.5]

Signaly je potreba definovat korektne. Nejjednodussi je dat tomu list.
np.arange dava list
np.repeat dava list, kazdou hodnotu dava n-krat podle druheho parametru
pouzij XXX.plot pro spojity cas
pouzij XXX.stem pro diskretni cas(vzorky)

ax_win.set_ylim([-1, 1])  takto muzu ohranicit osy
"""
unit_sig = signal.unit_impulse(1)
n = np.arange(0, 6)
x = np.repeat([0, 1, 0], 2)
#x = x + np.random.randn(len(x)) * 0.05  # přídání šumu
#h = [np.sin(2 * np.pi * n/12) for n in n]  # konvoluční funkce např. cos(np.pi * t) + 1
h = np.repeat([0.5, 0.5], 1)  # musis zadat uz hotovou impulsni odezvu
y = signal.convolve(x, h, mode='same')

fig, (ax_orig, ax_win, ax_filt) = plt.subplots(3, 1, sharex=True)
ax_orig.stem(n, x)
ax_orig.set_title('Original pulse')

ax_win.stem(h)
ax_win.set_title('Filter impulse response')

ax_filt.stem(n, y)
ax_filt.set_title('Filtered signal')
fig.show()
print(x, "\n", h, "\n", y)
