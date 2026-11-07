import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


DATABASE_FILE = Path("presence.db")
MATRICULE_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


def connect():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with closing(connect()) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                matricule TEXT NOT NULL UNIQUE,
                nom TEXT NOT NULL,
                actif INTEGER NOT NULL DEFAULT 1 CHECK (actif IN (0, 1))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                cours TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS attendance (
                session_id INTEGER NOT NULL REFERENCES sessions(id),
                student_id INTEGER NOT NULL REFERENCES students(id),
                statut TEXT NOT NULL DEFAULT 'absent'
                    CHECK (statut IN ('absent', 'present')),
                detected_at TEXT,
                PRIMARY KEY (session_id, student_id),
                CHECK (
                    (statut = 'absent' AND detected_at IS NULL)
                    OR (statut = 'present' AND detected_at IS NOT NULL)
                )
            );
            """
        )


def validate_matricule(matricule):
    if not MATRICULE_PATTERN.fullmatch(matricule):
        raise ValueError("Le matricule doit contenir uniquement lettres, chiffres, _ ou -.")


def add_student(matricule, nom):
    validate_matricule(matricule)
    with closing(connect()) as connection, connection:
        connection.execute(
            "INSERT INTO students (matricule, nom) VALUES (?, ?)",
            (matricule, nom),
        )


def get_student_by_matricule(matricule):
    validate_matricule(matricule)
    with closing(connect()) as connection:
        return connection.execute(
            "SELECT id, matricule, nom FROM students WHERE matricule = ? AND actif = 1",
            (matricule,),
        ).fetchone()


def get_active_students():
    with closing(connect()) as connection:
        return connection.execute(
            "SELECT id, matricule, nom FROM students WHERE actif = 1 ORDER BY matricule"
        ).fetchall()


def list_students():
    with closing(connect()) as connection:
        return connection.execute(
            "SELECT matricule, nom, actif FROM students ORDER BY matricule"
        ).fetchall()


def delete_all_students():
    with closing(connect()) as connection, connection:
        count = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        connection.execute("DELETE FROM attendance")
        connection.execute("DELETE FROM students")
        return count


def create_session(cours):
    students = get_active_students()
    if not students:
        raise RuntimeError("Aucun etudiant actif. Ajoutez d'abord les etudiants avec manage_students.py.")

    started_at = datetime.now().isoformat(timespec="seconds")
    with closing(connect()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO sessions (cours, started_at) VALUES (?, ?)",
            (cours, started_at),
        )
        session_id = cursor.lastrowid
        connection.executemany(
            "INSERT INTO attendance (session_id, student_id, statut) VALUES (?, ?, 'absent')",
            [(session_id, student["id"]) for student in students],
        )
    return session_id


def mark_present(session_id, student_id):
    detected_at = datetime.now().isoformat(timespec="seconds")
    with closing(connect()) as connection, connection:
        cursor = connection.execute(
            """UPDATE attendance
               SET statut = 'present', detected_at = ?
               WHERE session_id = ? AND student_id = ? AND statut = 'absent'""",
            (detected_at, session_id, student_id),
        )
        return cursor.rowcount == 1


def finish_session(session_id):
    ended_at = datetime.now().isoformat(timespec="seconds")
    with closing(connect()) as connection, connection:
        connection.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (ended_at, session_id),
        )


def get_session_attendance(session_id):
    with closing(connect()) as connection:
        return connection.execute(
            """SELECT students.matricule, students.nom, attendance.statut, attendance.detected_at
               FROM attendance
               JOIN students ON students.id = attendance.student_id
               WHERE attendance.session_id = ?
               ORDER BY students.matricule""",
            (session_id,),
        ).fetchall()