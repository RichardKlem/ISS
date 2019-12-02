"""  # start1
# ______________FIRST LESSON________________
# soundfile - neni potreba normalizace
import soundfile

data, fs = soundfile.read('music.wav')
data.min(), data.max()


from scipy.signal import tf2zpk
# takto dostaneme stejný výsledek jako v Matlabu a ekvivalentní tomu, jak máme b,a definované v ISS
a2 = [1, 2.3, -0.5]
b2 = [2.3, 0, 0]
z2, p2, _ = tf2zpk(b2, a2)
print(f'Nuly: {z2}')
print(f'Póly: {p2}')


# ukladani obrazku
import matplotlib.pyplot as plt
import numpy as np

plt.figure()
plt.plot(np.arange(100), np.arange(100))
plt.savefig('test.pdf')


 """  # end1

#"""  # start2
# ______________SECOND LESSON________________
#%matplotlib notebook
import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf
import IPython
from scipy.signal import spectrogram, lfilter, freqz, tf2zpk

s, fs = sf.read('music.wav')
s = s[:250000]
t = np.arange(s.size) / fs

plt.figure(figsize=(6, 3))
plt.plot(t, s)

# plt.gca() vraci handle na aktualni Axes objekt,
# ktery nam umozni kontrolovat ruzne vlastnosti aktualniho grafu
# napr. popisy os
# viz https://matplotlib.org/users/pyplot_tutorial.html#working-with-multiple-figures-and-axes
plt.gca().set_xlabel('$t[s]$')
plt.gca().set_title('Zvukový signál')

plt.tight_layout()



#"""  # end2


# """  start
# ______________THIRD LESSON________________





#"""  end