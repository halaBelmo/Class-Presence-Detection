import argparse
import os
from pathlib import Path
import time

import cv2

from attendance_db import get_student_by_matricule, initialize_database


def main():
    parser = argparse.ArgumentParser(description="Capturer les visages d'une personne.")
    parser.add_argument("matricule", help="Matricule deja present dans la base")
    parser.add_argument("--nombre", type=int, default=30, help="Nombre de photos a enregistrer")
    args = parser.parse_args()

    if args.nombre < 1:
        parser.error("--nombre doit etre superieur a zero")

    initialize_database()
    try:
        student = get_student_by_matricule(args.matricule)
    except ValueError as error:
        parser.error(str(error))
    if student is None:
        parser.error("Matricule inconnu. Ajoutez d'abord l'etudiant avec manage_students.py add.")

    output_dir = Path("dataset") / student["matricule"]
    output_dir.mkdir(parents=True, exist_ok=True)

    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError("Impossible d'ouvrir la webcam.")

    show_window = bool(os.environ.get("DISPLAY"))
    saved = len(list(output_dir.glob("face_*.jpg")))
    if show_window:
        print("Placez votre visage devant la camera; appuyez sur s pour enregistrer, q pour quitter.")
    else:
        print("Mode sans fenetre: capture automatique toutes les secondes; Ctrl+C pour quitter.")
    next_capture = 0.0

    try:
        while saved < args.nombre:
            success, frame = camera.read()
            if not success:
                print("Impossible de lire une image de la webcam.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
            face = max(faces, key=lambda box: box[2] * box[3]) if len(faces) else None

            if face is not None and show_window:
                x, y, width, height = face
                cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)

            if show_window:
                cv2.putText(
                    frame,
                    f"Photos: {saved}/{args.nombre} | s: enregistrer, q: quitter",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
                cv2.imshow("Inscription", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
            elif face is not None and time.monotonic() >= next_capture:
                key = ord("s")
                next_capture = time.monotonic() + 1.0
            else:
                key = 0
                time.sleep(0.02)

            if key == ord("s") and face is not None:
                x, y, width, height = face
                crop = gray[y : y + height, x : x + width]
                crop = cv2.resize(crop, (200, 200))
                saved += 1
                cv2.imwrite(str(output_dir / f"face_{saved:03d}.jpg"), crop)
                print(f"Photo enregistree: {saved}/{args.nombre}")
    finally:
        camera.release()
        if show_window:
            cv2.destroyAllWindows()

    print(f"{saved} photo(s) enregistree(s) pour {student['nom']} dans {output_dir}.")


if __name__ == "__main__":
    main()