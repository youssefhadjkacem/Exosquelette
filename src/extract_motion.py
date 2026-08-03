import cv2
import mediapipe as mp
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

video_path = PROJECT_ROOT / 'data' / 'videos' / 'video1.mp4'
cap = cv2.VideoCapture(str(video_path))

output_data = []
frame_number = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark
        
        # Bras droit
        r_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        r_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        r_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Bras gauche
        l_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        l_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        l_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        
        # Torse (pour référence/orientation)
        r_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        l_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]

        output_data.append([
            frame_number,
            r_shoulder.x, r_shoulder.y, r_shoulder.z,
            r_elbow.x, r_elbow.y, r_elbow.z,
            r_wrist.x, r_wrist.y, r_wrist.z,
            l_shoulder.x, l_shoulder.y, l_shoulder.z,
            l_elbow.x, l_elbow.y, l_elbow.z,
            l_wrist.x, l_wrist.y, l_wrist.z,
            r_hip.x, r_hip.y, r_hip.z,
            l_hip.x, l_hip.y, l_hip.z,
        ])

        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow('Motion Capture', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    frame_number += 1

cap.release()
cv2.destroyAllWindows()

with open(PROJECT_ROOT / 'data' / 'motion_data_v2.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['frame',
                      'r_shoulder_x', 'r_shoulder_y', 'r_shoulder_z',
                      'r_elbow_x', 'r_elbow_y', 'r_elbow_z',
                      'r_wrist_x', 'r_wrist_y', 'r_wrist_z',
                      'l_shoulder_x', 'l_shoulder_y', 'l_shoulder_z',
                      'l_elbow_x', 'l_elbow_y', 'l_elbow_z',
                      'l_wrist_x', 'l_wrist_y', 'l_wrist_z',
                      'r_hip_x', 'r_hip_y', 'r_hip_z',
                      'l_hip_x', 'l_hip_y', 'l_hip_z'])
    writer.writerows(output_data)

print(f"Terminé ! {len(output_data)} frames analysées.")
print("Fichier sauvegardé : motion_data_v2.csv")