import argparse
from pathlib import Path

import cv2

from attendance_db import get_student_by_matricule, initialize_database


DATASET_DIR = Path("dataset")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    parser = argparse.ArgumentParser(
        description="Importer les photos d'un etudiant depuis un dossier."
    )
    parser.add_argument("matricule", help="Matricule deja present dans la base")
    parser.add_argument("dossier", type=Path, help="Dossier contenant les photos source")
    args = parser.parse_args()

    initialize_database()
    try:
        student = get_student_by_matricule(args.matricule)
    except ValueError as error:
        parser.error(str(error))
    if student is None:
        parser.error("Matricule inconnu. Ajoutez d'abord l'etudiant avec manage_students.py add.")
    if not args.dossier.is_dir():
        parser.error(f"Dossier introuvable: {args.dossier}")

    image_paths = sorted(
        path
        for path in args.dossier.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not image_paths:
        parser.error("Aucune image JPG, PNG, BMP ou WEBP trouvee dans ce dossier.")

    detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    output_dir = DATASET_DIR / student["matricule"]
    output_dir.mkdir(parents=True, exist_ok=True)
    next_index = len(list(output_dir.glob("face_*.jpg"))) + 1
    imported = 0

    for image_path in image_paths:
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"Ignoree, image illisible: {image_path.name}")
            continue

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detection_image = cv2.equalizeHist(gray)
        faces = detector.detectMultiScale(
            detection_image,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(40, 40),
        )
        if len(faces) != 1:
            print(f"Ignoree, {len(faces)} visage(s) detecte(s): {image_path.name}")
            continue

        x, y, width, height = faces[0]
        crop = cv2.resize(gray[y : y + height, x : x + width], (200, 200))
        output_path = output_dir / f"face_{next_index:03d}.jpg"
        if cv2.imwrite(str(output_path), crop):
            print(f"Importee: {image_path.name} -> {output_path}")
            imported += 1
            next_index += 1
        else:
            print(f"Echec de l'enregistrement: {image_path.name}")

    print(f"{imported}/{len(image_paths)} photo(s) importee(s) pour {student['nom']}.")
    return 0 if imported else 1


if __name__ == "__main__":
    raise SystemExit(main())