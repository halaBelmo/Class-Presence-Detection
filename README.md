# TP Presence par reconnaissance faciale

Petit projet Python utilisant OpenCV (Haar Cascade et LBPH) et SQLite pour inscrire les etudiants, ouvrir une seance et faire passer les personnes reconnues de `absent` a `present`.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ajouter les etudiants

Ajoutez chaque etudiant dans la base SQLite avec son matricule et son nom :

```bash
python manage_students.py add 2024001 Alice
python manage_students.py add 2024002 Karim
python manage_students.py list
```

Pour supprimer tous les etudiants, leurs presences associees et toutes les photos de visages :

```bash
python manage_students.py clear
```

La commande demande confirmation. Ajoutez `--yes` pour la confirmer sans invite. Les seances passees et le fichier `presence.csv` sont conserves.

## Inscrire les visages

Le matricule doit deja exister dans la base. Il identifie le dossier de photos et evite les problemes de noms identiques :

```bash
python capture_faces.py 2024001
```

Dans la fenetre webcam, appuyez sur `s` pour enregistrer une photo et sur `q` pour quitter. Sans affichage graphique (par exemple dans un terminal Wayland sans XWayland), les photos sont prises automatiquement, une par seconde; utilisez `Ctrl+C` pour quitter. Par defaut, 30 photos sont demandees. Elles sont stockees dans `dataset/2024001/`.

## Importer des photos existantes

Mettez les photos d'un seul etudiant dans un dossier, puis donnez ce dossier et son matricule a la commande :

```text
photos/
	2024001/
		photo1.jpg
		photo2.png
```

```bash
python import_faces.py 2024001 photos/2024001
```

Les formats JPG, PNG, BMP et WEBP sont acceptes. Chaque image doit contenir exactement un visage; les images sans visage ou avec plusieurs visages sont ignorees. Les visages recadres sont ajoutes dans `dataset/<matricule>/`. Il faut ensuite redemarrer une seance pour recharger le modele.

## Demarrer une seance

```bash
python presence.py "TP vision"
```

La base cree une seance et initialise tous les etudiants actifs a `absent`. La webcam reste ouverte. Ouvrez `http://127.0.0.1:5000` dans votre navigateur : un cadre vert indique un etudiant reconnu, un cadre rouge un visage inconnu, et le tableau des presences est actualise automatiquement. Une presence est validee apres quinze images reconnues consecutives. Si aucun visage n'est detecte ou si le flux est trop sombre, un message apparait sur l'image. Faites `Ctrl+C` dans le terminal pour terminer la seance; le bilan complet s'affiche ensuite. Le seuil LBPH est defini par `CONFIDENCE_THRESHOLD` dans `camera_preview.py`.

Les donnees sont conservees dans `presence.db`. Le fichier historique `presence.csv` n'est pas importe. Les photos d'un ancien dossier `dataset/<nom>/` sont reutilisees seulement si ce nom correspond a un seul etudiant actif. Les photos et la base contiennent des donnees personnelles; utilisez uniquement des personnes ayant donne leur accord et supprimez ces fichiers a la fin du TP.