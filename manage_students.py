import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

from attendance_db import (
    add_student,
    delete_all_students,
    initialize_database,
    list_students,
)


DATASET_DIR = Path("dataset")


def main():
    parser = argparse.ArgumentParser(description="Gerer les etudiants du projet de presence.")
    commands = parser.add_subparsers(dest="command", required=True)

    add_command = commands.add_parser("add", help="Ajouter un etudiant")
    add_command.add_argument("matricule")
    add_command.add_argument("nom")
    commands.add_parser("list", help="Afficher les etudiants")
    clear_command = commands.add_parser(
        "clear", help="Supprimer tous les etudiants et les visages enregistres"
    )
    clear_command.add_argument(
        "--yes", action="store_true", help="Confirmer sans poser de question"
    )
    args = parser.parse_args()

    initialize_database()
    if args.command == "add":
        try:
            add_student(args.matricule, args.nom)
        except (ValueError, sqlite3.IntegrityError) as error:
            print(f"Erreur: {error}")
            return 1
        print(f"Etudiant ajoute: {args.matricule} - {args.nom}")
        return 0

    if args.command == "clear":
        if not args.yes:
            confirmation = input(
                "Supprimer tous les etudiants, presences associees et visages ? [o/N] "
            )
            if confirmation.strip().lower() not in {"o", "oui", "y", "yes"}:
                print("Suppression annulee.")
                return 0

        count = delete_all_students()
        if DATASET_DIR.is_symlink():
            raise RuntimeError(f"Le dossier dataset est un lien symbolique: {DATASET_DIR}")
        if DATASET_DIR.exists():
            shutil.rmtree(DATASET_DIR)
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        print(f"{count} etudiant(s) et toutes les donnees faciales ont ete supprimes.")
        print("Les seances passees et presence.csv sont conserves.")
        return 0

    students = list_students()
    if not students:
        print("Aucun etudiant dans la base.")
        return 0

    for student in students:
        status = "actif" if student["actif"] else "inactif"
        print(f"{student['matricule']} - {student['nom']} ({status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())