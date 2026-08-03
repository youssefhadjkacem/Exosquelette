import csv
import cv2
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
video_path = PROJECT_ROOT / 'data' / 'videos' / 'video1.mp4'
cap = cv2.VideoCapture(str(video_path))
fps = cap.get(cv2.CAP_PROP_FPS)
cap.release()

print(f"Framerate détecté : {fps} fps")

with open(PROJECT_ROOT / 'data' / 'motion_data_smoothed.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

num_frames = len(rows)

# Échelle : on veut que la distance épaule-coude soit environ 0.3m (30cm)
# MediaPipe donne des valeurs normalisées 0-1, donc on teste avec 1000mm
scale = 1000
output_path = PROJECT_ROOT / 'data' / 'motion_data.trc'
with open(output_path, 'w') as f:
    f.write("PathFileType\t4\t(X/Y/Z)\tmotion_data.trc\n")
    f.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
    f.write(f"{fps}\t{fps}\t{num_frames}\t3\tmm\t{fps}\t1\t{num_frames}\n")
    f.write("Frame#\tTime\tr_acromion\t\t\tr_humerus_epicondyle\t\t\tr_radius_styloid\t\t\n")
    f.write("\t\tX1\tY1\tZ1\tX2\tY2\tZ2\tX3\tY3\tZ3\n\n")

    for i, row in enumerate(rows):
        time = i / fps
        
        # X reste pareil (gauche-droite)
        sx = float(row['shoulder_x']) * scale
        ex = float(row['elbow_x']) * scale
        wx = float(row['wrist_x']) * scale

        # Y est INVERSÉ (MediaPipe: bas=positif, OpenSim: haut=positif)
        sy = (1 - float(row['shoulder_y'])) * scale
        ey = (1 - float(row['elbow_y'])) * scale
        wy = (1 - float(row['wrist_y'])) * scale

        # Z (profondeur) - on réduit son influence car peu fiable en mono-caméra
        sz = float(row['shoulder_z']) * scale * 0.3
        ez = float(row['elbow_z']) * scale * 0.3
        wz = float(row['wrist_z']) * scale * 0.3

        f.write(f"{i+1}\t{time:.4f}\t{sx:.4f}\t{sy:.4f}\t{sz:.4f}\t{ex:.4f}\t{ey:.4f}\t{ez:.4f}\t{wx:.4f}\t{wy:.4f}\t{wz:.4f}\n")

print(f"Fichier TRC créé : motion_data.trc")
print(f"Nombre de frames : {num_frames}")