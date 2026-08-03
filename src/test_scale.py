import csv
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
with open(PROJECT_ROOT / 'data' / 'motion_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

def distance(p1, p2):
    return math.sqrt(sum((a-b)**2 for a, b in zip(p1, p2)))

# Segment 1 : épaule -> coude (longueur du bras supérieur, ne change pas)
seg1_distances = []
# Segment 2 : coude -> poignet (longueur de l'avant-bras, ne change pas)
seg2_distances = []

for row in rows[:60]:  # 2 secondes de données
    shoulder = (float(row['shoulder_x']), float(row['shoulder_y']), float(row['shoulder_z']))
    elbow = (float(row['elbow_x']), float(row['elbow_y']), float(row['elbow_z']))
    wrist = (float(row['wrist_x']), float(row['wrist_y']), float(row['wrist_z']))
    
    seg1_distances.append(distance(shoulder, elbow))
    seg2_distances.append(distance(elbow, wrist))

avg_seg1 = sum(seg1_distances) / len(seg1_distances)
avg_seg2 = sum(seg2_distances) / len(seg2_distances)

print(f"Segment épaule-coude (normalisé): {avg_seg1:.4f}")
print(f"Segment coude-poignet (normalisé): {avg_seg2:.4f}")
print(f"Écart-type segment 1: {(max(seg1_distances)-min(seg1_distances)):.4f}")
print(f"Écart-type segment 2: {(max(seg2_distances)-min(seg2_distances)):.4f}")

# Bras supérieur ~30cm, avant-bras ~27cm (moyennes anatomiques)
scale_from_seg1 = 300 / avg_seg1
scale_from_seg2 = 270 / avg_seg2

print(f"\nScale basé sur épaule-coude: {scale_from_seg1:.2f}")
print(f"Scale basé sur coude-poignet: {scale_from_seg2:.2f}")