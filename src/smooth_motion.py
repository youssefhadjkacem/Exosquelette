import csv
import numpy as np
from pathlib import Path
from scipy.signal import butter, filtfilt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
with open(PROJECT_ROOT / 'data' / 'motion_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

columns = ['shoulder_x', 'shoulder_y', 'shoulder_z',
           'elbow_x', 'elbow_y', 'elbow_z',
           'wrist_x', 'wrist_y', 'wrist_z']

data = {col: np.array([float(row[col]) for row in rows]) for col in columns}

fps = 30
cutoff = 6
nyquist = fps / 2
normal_cutoff = cutoff / nyquist
b, a = butter(4, normal_cutoff, btype='low', analog=False)

smoothed_data = {col: filtfilt(b, a, data[col]) for col in columns}

with open(PROJECT_ROOT / 'data' / 'motion_data_smoothed.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['frame'] + columns)
    for i in range(len(rows)):
        writer.writerow([i] + [smoothed_data[col][i] for col in columns])

print(f"Lissage terminé ! {len(rows)} frames traitées.")
print(f"Fichier créé : motion_data_smoothed.csv")