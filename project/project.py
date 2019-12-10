import os
import sys
import statistics

"""  # start1
# ______________FIRST LESSON________________
# soundfile - neni potreba normalizace
import soundfile

s, fs = soundfile.read('beethoven.wav')
s.min(), s.max()


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

"""  # end1

#"""  # start2
# ______________SECOND LESSON________________
import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf
import IPython
from scipy.signal import spectrogram, lfilter, freqz, tf2zpk
from scipy.stats import pearsonr

s, fs = sf.read('sx368.wav')

s = s[:s.size]
t = np.arange(s.size) / fs
print(s.size)
plt.figure(figsize=(6, 3))
plt.plot(t, s)

# plt.gca() vraci handle na aktualni Axes objekt,
# ktery nam umozni kontrolovat ruzne vlastnosti aktualniho grafu
# napr. popisy os
# viz https://matplotlib.org/users/pyplot_tutorial.html#working-with-multiple-figures-and-axes
plt.gca().set_xlabel('$t[s]$')
plt.gca().set_title('Zvukový signál')

plt.tight_layout()
plt.show()


s = s - statistics.mean(s)  # usmerneni od DC slozky

odkud = 0     # začátek segmentu v sekundách - od zacatku
kolik = 0.02  # délka segmentu v sekundách - 20ms

odkud_vzorky = int(odkud * fs)          # začátek segmentu ve vzorcích
pokud_vzorky = int((odkud+kolik) * fs)  # konec segmentu ve vzorcích

s_seg = s[odkud_vzorky:pokud_vzorky]
#print(s_seg)
#sys.exit(0)
N = s_seg.size  # sirka matice spektrogramu
print(N)
s_seg_spec = np.fft.fft(s_seg)
print(len(s_seg_spec))
G = 10 * np.log10(1/N * np.abs(s_seg_spec)**2)
print(len(G))

_, ax = plt.subplots(2, 1)

# np.arange(n) vytváří pole 0..n-1 podobně jako obyč Pythonovský range
ax[0].plot(np.arange(s_seg.size) / fs + odkud, s_seg)
ax[0].set_xlabel('$t[s]$')
ax[0].set_title('Segment signalu $s$')
ax[0].grid(alpha=0.5, linestyle='--')

f = np.arange(G.size) / N * fs
# zobrazujeme prvni pulku spektra
ax[1].plot(f[:f.size//2+1], G[:G.size//2+1])
ax[1].set_xlabel('$f[Hz]$')
ax[1].set_title('Spektralni hustota vykonu [dB]')
ax[1].grid(alpha=0.5, linestyle='--')

plt.tight_layout()
plt.show()

f, t, sgr = spectrogram(s, fs, window='hamming', noverlap=0.015*fs, nfft=255*2+1)  #prekryti 15ms

print((sgr.shape))
# prevod na PSD
# (ve spektrogramu se obcas objevuji nuly, ktere se nelibi logaritmu, proto +1e-20)
sgr_log = 10 * np.log10(sgr+1e-20)

plt.figure(figsize=(9, 3))
plt.pcolormesh(t, f, sgr_log)
plt.gca().set_xlabel('Čas [s]')
plt.gca().set_ylabel('Frekvence [Hz]')
cbar = plt.colorbar()
cbar.set_label('Spektralní hustota výkonu [dB]', rotation=270, labelpad=15)

plt.tight_layout()

plt.show()

A = [[0]*256 for i in range(16)]  # naplním nulami
# doplnim jednicky vzdy o jeedna posunute
for j in range(16):
    for i in range(16):
        A[j][i + (j*16)] = 1

F = np.matmul(A, sgr)  # F = A * P

# ____________   UKOL 5  _____________
def column(matrix, i):
    return [row[i] for row in matrix]

s_q, fs_q = sf.read('q2_upr.wav') #načtení frekvence a signálu
s_q = s_q - s_q.mean(axis=0) #ustřednění signálu pomocí odečtení střední hodnoty

f_q, t_q, sgr_q = spectrogram(s_q, fs_q, window='hamming', noverlap=0.015*fs, nfft=256*2-1)


F_q = np.matmul(A, sgr_q)  # F_q = A * P_q

print(F.shape)
print(F_q.shape)

pears_result_res_list = [] #list pro ukládání hodnot z funkce pearsonr
#průchod
pears_result = 0  # aktualni soucet korelaci
for i in range(0, sgr.shape[1] - sgr_q.shape[1]):
    if i % 250 == 0:
        print(i)
    for j in range(sgr_q.shape[1]):
        pears_result += (pearsonr(column(F_q, j), column(F, i + j))[0])
    pears_result_res_list.append(pears_result)
    pears_result = 0
print(max(pears_result_res_list))
print(pears_result_res_list.index(max(pears_result_res_list)))


#plt.savefig('test.pdf')
#"""  # end2


# """  start
# ______________THIRD LESSON________________





#"""  end