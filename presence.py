import argparse
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from attendance_db import (
    create_session,
    finish_session,
    get_active_students,
    get_session_attendance,
    initialize_database,
)
from camera_preview import create_app


DATASET_DIR = Path("dataset")


def train_recognizer():
    images = []
    labels = []
    students_by_label = {}

    if not DATASET_DIR.is_dir():
        raise RuntimeError("Dossier dataset introuvable. Inscrivez d'abord les visages avec capture_faces.py.")

    students = get_active_students()
    name_counts = Counter(student["nom"].casefold() for student in students)
    for student in students:
        student_id = student["id"]
        students_by_label[student_id] = student
        student_dir = DATASET_DIR / student["matricule"]
        image_paths = sorted(student_dir.glob("*.jpg"))
        if not image_paths and name_counts[student["nom"].casefold()] == 1:
            legacy_dir = DATASET_DIR / student["nom"]
            if legacy_dir.is_dir() and legacy_dir.resolve().parent == DATASET_DIR.resolve():
                image_paths = sorted(legacy_dir.glob("*.jpg"))

        for image_path in image_paths:
            image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if image is not None:
                images.append(cv2.resize(image, (200, 200)))
                labels.append(student_id)

    if not images:
        raise RuntimeError("Aucun visage inscrit pour les etudiants actifs. Utilisez capture_faces.py <matricule>.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(images, np.asarray(labels, dtype=np.int32))
    return recognizer, students_by_label


def main():
    parser = argparse.ArgumentParser(description="Pointer les presences pour une seance.")
    parser.add_argument("cours", help="Nom du cours ou de la seance")
    args = parser.parse_args()

    initialize_database()
    recognizer, students_by_label = train_recognizer()
    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError("Impossible d'ouvrir la webcam.")

    session_id = create_session(args.cours)
    app = create_app(camera, detector, recognizer, students_by_label, session_id)
    print(f"Seance {session_id} demarree: {args.cours}")
    print("Ouvrez http://127.0.0.1:5000 dans votre navigateur. Ctrl+C pour terminer.")

    try:
        app.run(host="127.0.0.1", port=5000, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Arret de la seance.")
    finally:
        camera.release()
        finish_session(session_id)

    attendance = get_session_attendance(session_id)
    present_count = sum(row["statut"] == "present" for row in attendance)
    print(f"Seance terminee: {present_count}/{len(attendance)} present(s).")
    for row in attendance:
        print(f"{row['statut'].capitalize()}: {row['matricule']} - {row['nom']}")


if __name__ == "__main__":
    main()