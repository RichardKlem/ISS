import numpy
import scipy as sp
import matplotlib.pylab as plt

t = sp.arange(0, 10, 1/100)
plt.plot(t, sp.sin(1.7 * 2 * sp.pi * t) + sp.sin(1.9 * 2 * sp.pi * t))
plt.show()
