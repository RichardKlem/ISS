"""
jméno:           Richard Klem
školní e-mail:   xklemr00@fit.vutbr.cz
datum odevzdání: 16.12.2019
"""
import os
import statistics
import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf
from scipy.signal import spectrogram
from scipy.stats import pearsonr

work_dir = os.path.dirname(os.getcwd())
sentences_root = 'sentences'
queries_root = 'queries'
sentence_name = 'sa1.wav'
query1_name = 'q1.wav'
query2_name = 'q2.wav'
sentence = os.path.join(work_dir, sentences_root, sentence_name)
query1 = os.path.join(work_dir, queries_root, query1_name)  # trustworthy
query2 = os.path.join(work_dir, queries_root, query2_name)  # pathological

with open(sentence, mode='rb') as sentence:
    s, fs = sf.read(sentence)

# s = s[:s.size]  #TODO je to treba???
t = np.arange(s.size) / fs
plt.figure(figsize=(9, 3))
plt.plot(t, s)

plt.gca().set_title('"trustworthy" and "pathological" vs. {}'.format(sentence_name))
plt.gca().set_xlabel('t')
plt.gca().set_ylabel('signal')
plt.tight_layout()
plt.show()

s = s - statistics.mean(s)  # usmerneni od DC slozky

f, t, sgr = spectrogram(s, fs, window='hamming', nperseg=int(0.025 * fs),
                        noverlap=0.015 * fs, nfft=255 * 2 + 1)

# prevod na PSD
# (ve spektrogramu se obcas objevuji nuly, ktere se nelibi logaritmu, proto +1e-20)
sgr_log = 10 * np.log10(sgr + 1e-20)

plt.figure(figsize=(9, 3))
plt.pcolormesh(t, f, sgr_log)
plt.gca().set_title('sa1')
plt.gca().set_xlabel('Time')
plt.gca().set_ylabel('Frequency')
cbar = plt.colorbar()
cbar.set_label('Power spectral density', rotation=270, labelpad=15)

plt.tight_layout()

plt.show()

A = [[0] * 256 for i in range(16)]  # naplním nulami
# doplním jedničky vždy o jedničku posunuté
for j in range(16):
    for i in range(16):
        A[j][i + (j * 16)] = 1

# ____________   UKOL 6 - features vety  _____________
F = np.matmul(A, sgr_log)  # F = A * P
f2 = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
plt.figure(figsize=(9, 3))
plt.pcolormesh(t, f2, F)
plt.gca().set_xlabel('t')
plt.gca().set_ylabel('features')
plt.gca().invert_yaxis()  # prohozeni osy y vzhuru nohama
plt.tight_layout()
plt.show()


# ____________   UKOL 5  _____________
def column(matrix, i):
    return [row[i] for row in matrix]


s_q, fs_q = sf.read(query1)  # načtení frekvence a signálu
s_q = s_q - s_q.mean(axis=0)  # ustřednění signálu pomocí odečtení střední hodnoty

f_q, t_q, sgr_q = spectrogram(s_q, fs_q, window='hamming', nperseg=int(0.025 * fs),
                              noverlap=0.015 * fs, nfft=256 * 2 - 1)
F_q = np.matmul(A, sgr_q)  # F_q = A * P_q

s_q, fs_q = sf.read(query2)  # načtení frekvence a signálu
s_q = s_q - s_q.mean(axis=0)  # ustřednění signálu pomocí odečtení střední hodnoty

f_q2, t_q2, sgr_q2 = spectrogram(s_q, fs_q, window='hamming', nperseg=int(0.025 * fs),
                                 noverlap=0.015 * fs, nfft=256 * 2 - 1)

F_q2 = np.matmul(A, sgr_q2)  # F_q = A * P_q

pears_result_res_list = []  # list pro ukládání hodnot z funkce pearsonr
pears_result = 0  # aktualni soucet korelaci
for i in range(0, sgr.shape[1] - sgr_q.shape[1], 1):
    for j in range(sgr_q.shape[1]):
        pears_result += (pearsonr(column(F_q, j), column(F, i + j))[0])
    pears_result /= sgr_q.shape[1]  # děleno počtem vektorů pro zjištění
                                    # pravděpodobnosti výskytu
    pears_result_res_list.append(pears_result)
    pears_result = 0

pears_result_res_list2 = []  # list pro ukládání hodnot z funkce pearsonr
# průchod
pears_result2 = 0  # aktualni soucet korelaci
for i in range(0, sgr.shape[1] - sgr_q2.shape[1], 1):
    for j in range(sgr_q2.shape[1]):
        pears_result2 += (pearsonr(column(F_q2, j), column(F, i + j))[0])
    pears_result2 /= sgr_q2.shape[1]
    pears_result_res_list2.append(pears_result2)
    pears_result2 = 0

plt.figure(figsize=(9, 3))

plt.plot(np.arange(len(pears_result_res_list)) / 100, pears_result_res_list, label='trustworthy')
plt.plot(np.arange(len(pears_result_res_list2)) / 100, pears_result_res_list2,
         label='pathological')

plt.gca().set_xlim(right=s.size / fs)
plt.legend()
plt.gca().set_xlabel('t')
plt.gca().set_ylabel('scores')
# plt.gca().set_title('Průběh skóre')
# plt.gca().set

plt.tight_layout()
plt.show()

"""
ax = plt.plot()

# np.arange(n) vytváří pole 0..n-1 podobně jako obyč Pythonovský range
ax.plot(np.arange(((len(pears_result_res_list)))), pears_result_res_list)
ax.set_xlabel('$t[s]$')
ax.set_title('Segment signalu $s$')
ax.grid(alpha=0.5, linestyle='--')



plt.tight_layout()
plt.show()

#plt.savefig('test.pdf')
#"""
