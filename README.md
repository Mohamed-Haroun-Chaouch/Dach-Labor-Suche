# Laborsuche DACH - Coding Challenge 🏥

Eine interaktive Karte zur Suche von Anbietern für DEXA Body Composition Scans und Selbstzahler-Blutuntersuchungen. Erstellt für die Werkstudentenstelle bei Bahmann Coaching.

## 🧠 Strategie & Architektur (Der "Human-in-the-Loop" Ansatz)

Die größte Herausforderung dieser Aufgabe ist die Datenqualität: Keine API der Welt weiß zuverlässig, ob eine Radiologie nur Knochendichtemessungen oder auch echte Body Composition Scans anbietet.

Um Overengineering zu vermeiden, habe ich einen hybriden PoC (Proof of Concept) für die Region **Berlin** gebaut:

1. **Automatisierung (Python):** Ein Python-Skript fragt die moderne _Google Places API (New)_ ab, um Radiologien und Labore zu finden und exakte GPS-Daten zu extrahieren.
2. **Datenbank (`data.json`):** Die Daten landen in einer leichtgewichtigen JSON-Datei. Initial stehen alle spezifischen Leistungen auf `false` und erhalten das Flag `verified_manually: false`.
3. **Manuelle Verifizierung:** Die eigentliche medizinische Qualifikation der Anbieter wird (z.B. durch telefonische Nachfrage) verifiziert und im JSON mit einem Flag (`verified_manually: true`) und Notizen dokumentiert.
4. **Frontend:** Ein Vanilla JS & Leaflet.js Frontend liest die Daten und zeigt sie interaktiv an. Es visualisiert sofort, welche Datensätze geprüft sind (✅) und welche noch verifiziert werden müssen (⚠️).

## 🚀 Setup & Starten

### Option A: Mit Docker (Empfohlen)

1. Repository klonen und in den Ordner wechseln.
2. Image bauen: `docker build -t dach-labor-suche .`
3. Container starten: `docker run -p 8000:8000 dach-labor-suche`
4. Im Browser öffnen: [http://localhost:8000/frontend/](http://localhost:8000/frontend/)

### Option B: Lokal mit Python

1. In den Ordner wechseln: `cd dach-labor-suche`
2. Server starten: `python -m http.server 8000`
3. Im Browser öffnen: [http://localhost:8000/frontend/](http://localhost:8000/frontend/)

_(Hinweis: Um neue Daten via Google Places API zu scrapen, muss eine `.env` Datei mit einem `GOOGLE_PLACES_API_KEY` angelegt und das Python-Environment aus `scraper/requirements.txt` installiert werden. Der Befehl lautet dann `python scraper/main.py`)_

## 🛠️ Entscheidungen & Trade-offs

- **Keine relationale Datenbank:** Für diese Art von Geo-Daten, die sich selten ändern, ist eine `data.json` performanter und leichter wartbar als eine SQL-Datenbank (KISS-Prinzip).
- **Leaflet.js statt Google Maps JS API:** Leaflet benötigt keine API-Keys im Frontend und nutzt kostenlose OpenStreetMap-Tiles. Das macht das Projekt portabler.

## 🔮 Was ich mit mehr Zeit tun würde

- **Scraping-Erweiterung:** Den Scraper so anpassen, dass er automatisiert Websites von Praxen nach Keywords ("IGeL", "Body Composition", "Selbstzahler") durchsucht, um den Verifizierungsprozess zu beschleunigen.
- **Clustering:** Bei einer Skalierung auf den gesamten DACH-Raum `Leaflet.markercluster` einbauen, damit die Karte bei hunderten Markern nicht unübersichtlich wird.
- **Frontend-Framework:** Für ein größeres Dashboard auf React oder Vue.js umsteigen.
