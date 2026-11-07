import cv2
from flask import Flask, Response, jsonify, render_template_string

from attendance_db import get_session_attendance, mark_present


CONFIDENCE_THRESHOLD = 50
MIN_PRESENT_HITS = 15
MIN_FRAME_BRIGHTNESS = 15
MIN_FACE_SIZE = (80, 80)
NO_FACE_WARNING_FRAMES = 30


def create_app(camera, detector, recognizer, students_by_label, session_id):
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template_string(
            """<!doctype html>
            <html lang="fr">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>Pointage de presence</title>
              <style>
                body { margin: 0; background: #f3f5f4; color: #17211d; font: 16px sans-serif; }
                main { max-width: 1000px; margin: 28px auto; padding: 0 18px; }
                h1 { margin: 0 0 6px; font-size: 24px; }
                p { margin: 0 0 18px; color: #52615a; }
                img { display: block; width: 100%; max-height: 65vh; object-fit: contain; background: #101613; }
                table { width: 100%; margin-top: 18px; border-collapse: collapse; background: white; }
                th, td { padding: 10px 12px; border-bottom: 1px solid #e1e7e3; text-align: left; }
                th { color: #52615a; font-size: 13px; }
                .present { color: #147d45; font-weight: 700; }
                .absent { color: #a13b32; font-weight: 700; }
                @media (max-width: 600px) { main { margin: 16px auto; } th, td { padding: 8px 6px; } }
              </style>
            </head>
            <body>
              <main>
                <h1>Pointage de presence</h1>
                <p>Seance {{ session_id }} · cadre vert : etudiant reconnu · rouge : visage inconnu</p>
                <img src="/video" alt="Flux de la webcam">
                <table>
                  <thead><tr><th>Matricule</th><th>Etudiant</th><th>Etat</th><th>Heure</th></tr></thead>
                  <tbody id="attendance"></tbody>
                </table>
              </main>
              <script>
                async function refreshAttendance() {
                  const response = await fetch('/api/attendance');
                  const rows = await response.json();
                  document.getElementById('attendance').innerHTML = rows.map(row =>
                    `<tr><td>${row.matricule}</td><td>${row.nom}</td>` +
                    `<td class="${row.statut}">${row.statut}</td><td>${row.heure || '-'}</td></tr>`
                  ).join('');
                }
                refreshAttendance();
                setInterval(refreshAttendance, 1000);
              </script>
            </body>
            </html>""",
            session_id=session_id,
        )

    @app.get("/api/attendance")
    def attendance_status():
        rows = get_session_attendance(session_id)
        return jsonify(
            [
                {
                    "matricule": row["matricule"],
                    "nom": row["nom"],
                    "statut": row["statut"],
                    "heure": row["detected_at"],
                }
                for row in rows
            ]
        )

    @app.get("/video")
    def video():
      def generate_frames():
        consecutive_hits = {}
        no_face_frames = 0
        while True:
          success, frame = camera.read()
          if not success:
            break

          gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          camera_too_dark = float(gray.mean()) < MIN_FRAME_BRIGHTNESS
          if camera_too_dark:
            faces = []
          else:
            faces = detector.detectMultiScale(
              gray,
              scaleFactor=1.2,
              minNeighbors=5,
              minSize=MIN_FACE_SIZE,
            )
          seen_students = set()
          no_face_frames = 0 if len(faces) else no_face_frames + 1

          for x, y, width, height in faces:
            crop = cv2.resize(gray[y : y + height, x : x + width], (200, 200))
            label, confidence = recognizer.predict(crop)

            if confidence <= CONFIDENCE_THRESHOLD and label in students_by_label:
              student = students_by_label[label]
              student_id = student["id"]
              if student_id not in seen_students:
                consecutive_hits[student_id] = consecutive_hits.get(student_id, 0) + 1
                seen_students.add(student_id)
              hit_count = consecutive_hits[student_id]
              color = (0, 200, 0)
              text = f"{student['matricule']} ({confidence:.0f})"
              if hit_count < MIN_PRESENT_HITS:
                text += f" {hit_count}/{MIN_PRESENT_HITS}"
              elif hit_count == MIN_PRESENT_HITS and mark_present(session_id, student_id):
                print(f"Present: {student['matricule']} - {student['nom']}")
            else:
              color = (0, 0, 255)
              text = "Inconnu"

            cv2.rectangle(frame, (x, y), (x + width, y + height), color, 2)
            cv2.putText(
              frame,
              text,
              (x, max(y - 10, 20)),
              cv2.FONT_HERSHEY_SIMPLEX,
              0.7,
              color,
              2,
            )

          for student_id in consecutive_hits.keys() - seen_students:
            consecutive_hits[student_id] = 0

          if camera_too_dark:
            cv2.putText(
              frame,
              "Image trop sombre - ouvrez l'obturateur de la webcam",
              (10, 30),
              cv2.FONT_HERSHEY_SIMPLEX,
              0.6,
              (0, 0, 255),
              2,
            )
          elif no_face_frames >= NO_FACE_WARNING_FRAMES:
            cv2.putText(
              frame,
              "Aucun visage detecte - placez-vous face a la webcam",
              (10, 30),
              cv2.FONT_HERSHEY_SIMPLEX,
              0.6,
              (0, 0, 255),
              2,
            )

          encoded, buffer = cv2.imencode(".jpg", frame)
          if encoded:
            yield (
              b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
              + buffer.tobytes()
              + b"\r\n"
            )

      return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
      )

    return app