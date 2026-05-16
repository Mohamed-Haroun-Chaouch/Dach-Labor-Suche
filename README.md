# Laborsuche DACH - KI-gestützte Daten-Pipeline 🏥

Eine interaktive Karten-Applikation zur Suche von verifizierten Anbietern für DEXA Body Composition Scans und Selbstzahler-Blutuntersuchungen.

## 🧠 Strategie & Fokus

Dieses Projekt konzentriert sich auf zwei hochspezifische medizinische Dienstleistungen für Sportler und Selbstoptimierer:

1. **DEXA Scans für Body Composition** (Körperfett/Muskelmasse, _nicht_ nur Osteoporose-Vorsorge).
2. **Blutuntersuchungen als Selbstzahler** (Direktlabore).

**Hinweis zum Selbstzahler-Status:** Anstatt im Datensatz lediglich ein statisches Datenfeld `Selbstzahler möglich? (ja/nein)` mitzuführen, wurde dieser Aspekt direkt in den Kern-Algorithmus integriert. Die Pipeline sucht proaktiv nach Praxen/Laboren, die "IGeL"-Leistungen, Direktzugang und Wunschlabore anbieten. Praxen, die zwingend einen Überweisungsschein verlangen oder nur Kassenpatienten behandeln, werden durch die KI direkt im Scraping-Prozess verworfen.

---

## 🛠️ Evolution der Architektur: Wie aus Fehlern die finale Lösung wurde

Die Entwicklung dieser Pipeline war ein iterativer Prozess. Die größte Herausforderung war das sogenannte "Dirty Data"-Problem. Hier sind die architektonischen Entscheidungen und wie sich das System Schritt für Schritt verbessert hat:

### Iteration 1: Die Grenzen der Google API

- **Erster Ansatz:** Eine einfache Abfrage der Google Places API nach "DEXA Scan".
- **Das Problem:** Google klassifiziert fast alles als "Radiologie". Über 80 % der Ergebnisse waren klassische Radiologien, die _ausschließlich_ medizinische Knochendichtemessung (Lendenwirbelsäule) für ältere Patienten anbieten, aber keine Körperanalyse für Sportler.
- **Die Entscheidung:** Die Google API reicht nicht als "Single Source of Truth". Wir brauchen einen Scraper (`BeautifulSoup`), der die tatsächliche Website der Praxis besucht und den dortigen Text extrahiert.

### Iteration 2: Von starren Keywords zu NLP (SBERT)

- **Zweiter Ansatz:** Ein lexikalischer Filter, der die gescrapten Websites nach Wörtern wie "Körperfett" oder "Zusammensetzung" durchsucht.
- **Das Problem (Recall-Falle):** Ärzte nutzen oft andere Formulierungen (z.B. "Medizinische Fitnessanalyse"). Ein reiner Keyword-Filter übersieht diese echten Treffer (False Negatives). Gleichzeitig schlägt der Filter fälschlicherweise an (False Positives), wenn eine Praxis schreibt: _"Wir messen Knochendichte, aber **kein** Körperfett."_
- **Die Entscheidung:** Wechsel von Regex/Keywords zu echter Semantik. Ich habe ein lokales Sentence-BERT Modell (`paraphrase-multilingual-MiniLM`) implementiert. Es berechnet die mathematische Ähnlichkeit (Cosine Similarity) der Website-Sätze zu einem definierten Referenz-Satz. SBERT versteht den Kontext und erkennt, ob eine Praxis das Thema wirklich anbietet.

### Iteration 3: Der hybride Filter (Semantik + Guardrails)

- **Dritter Ansatz:** Ausschließliche Nutzung von SBERT.
- **Das Problem:** SBERT ist mächtig, wurde aber manchmal von hochspezialisierten Rheumatologie- oder Endokrinologie-Kliniken "ausgetrickst", die ähnlich strukturierte Sätze verwenden.
- **Die Entscheidung:** Ein hybrides Ensemble-Modell. SBERT liefert 70 % der Entscheidungskraft (für hohen Recall). Die alten Keywords wurden als "Guardrails" (TF-IDF Proxy) wieder eingeführt und steuern 30 % bei. Strenge Negativ-Keywords (wie "Knochenschwund" oder "Überweisung zwingend") ziehen den Confidence-Score massiv nach unten. Praxen mit einem finalen Score > 0.55 erhalten das Flag `verification_status: "ai_verified"`.

### Iteration 4: Spatial Deduplication (Geo-Filter)

- **Das Problem:** Bei der Ausweitung auf 11 Metropolen zeigte sich, dass in großen Kliniken oft mehrere Ärzte mit eigenen Google-IDs registriert sind. Das führte zu überlappenden, identischen Pins auf der Karte.
- **Die Entscheidung:** Eine klassische ID-Filterung reicht nicht. Ich habe eine räumliche Deduplizierung (Spatial Deduplication) implementiert. Die GPS-Koordinaten werden auf 3 Nachkommastellen gerundet (entspricht ca. 110m Radius). Befindet sich ein Anbieter der gleichen Kategorie im selben Radius, wird er als Duplikat verworfen.

### Iteration 5: Tooling für die Qualitätskontrolle (QA)

- **Das Problem:** Bei über 600 gescrapten Datensätzen ist eine manuelle Überprüfung aller Ergebnisse extrem ineffizient.
- **Die Entscheidung:** Um den nachgelagerten "Human-in-the-Loop"-Prozess zu skalieren, generiert das Skript am Ende automatisch eine `audit_samples.json`. Ein QA-Team muss so nicht hunderte Praxen prüfen, sondern kann anhand einer kleinen Stichprobe von 22 Datensätzen (High/Low Confidence) die Genauigkeit des Modells statistisch validieren und bei Bedarf den Threshold anpassen.

---

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

### Die KI-Pipeline neu ausführen (Scraping)

Um tagesaktuelle Daten zu ziehen oder das KI-Modell anzupassen:

1. `.env` Datei mit `GOOGLE_PLACES_API_KEY=dein_key` anlegen.
2. Python-Umgebung einrichten: `pip install -r scraper/requirements.txt`
3. Scraper starten: `python scraper/main.py`
   _(Hinweis: Der Lauf für 11 Städte dauert ca. 10-15 Minuten, da hunderte Websites im Hintergrund analysiert und durch das Transformer-Modell berechnet werden.)_

---

## 🔮 Was ich mit mehr Zeit/Budget tun würde

- **Echtes LLM statt statistischer Proxys:** Aktuell imitiert das System die Fähigkeiten eines LLMs durch eine Kombination aus semantischer Ähnlichkeit (SBERT) und TF-IDF-basierten Keywords. In einer produktiven Enterprise-Umgebung würde ich einen echten LLM-Agenten (z.B. GPT-4o-mini oder Claude 3.5 Haiku) einsetzen, der die HTML-Texte via RAG (Retrieval-Augmented Generation) liest und evaluiert. Das garantiert eine noch höhere Accuracy und ein robusteres Verständnis von Nuancen auf Praxis-Websites.
- **CI/CD Pipeline:** Den Python-Scraper als GitHub Action aufsetzen, sodass die Daten einmal im Monat vollautomatisch aktualisiert und in den Main-Branch gepusht werden.
- **Frontend-Framework:** Portierung der Vanilla-JS Applikation zu einem modernen React/Next.js Dashboard mit Server-Side-Rendering (SSR) für bessere SEO und dynamisches Filtern.
