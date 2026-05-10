import os
import json
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
import torch

# Environment Variablen laden
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
BASE_URL = "https://places.googleapis.com/v1/places:searchText"

print("🤖 Lade KI-Modell (Sentence-BERT)...")
# Ein schnelles, mehrsprachiges Transformer-Modell
sbert_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Unsere zwei verschiedenen "Ground Truth" Referenz-Sätze für die KI
REF_EMBEDDINGS = {
    "dexa": sbert_model.encode("Wir bieten DEXA Scans zur Messung von Körperfettanteil, Körperzusammensetzung und Muskelmasse für Sportler an.", convert_to_tensor=True),
    "blood_lab": sbert_model.encode("Wir bieten Blutuntersuchungen, Blutbild und Laboranalysen für Selbstzahler ohne ärztliche Überweisung an.", convert_to_tensor=True)
}

def analyze_website_text(url, category_id):
    """
    Hybrid NLP Classifier (SBERT + Keyword/TF-IDF Proxy).
    Passt sich dynamisch an DEXA oder Blutlabor an und gibt den reinen Confidence Score zurück.
    """
    if not url: 
        return 0.0, "Keine Website vorhanden."
        
    try:
        # 1. Website abrufen (Timeout auf 5 Sekunden)
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        if len(text) < 100: 
            return 0.0, "Zu wenig Text für KI-Analyse."

        # 2. Dynamische Keywords je nach Kategorie
        if category_id == "dexa":
            pos_kw = ["körperfett", "muskelmasse", "body composition", "sportmedizin", "leistungsdiagnostik", "fettanteil", "zusammensetzung", "fitnessanalyse"]
            neg_kw = ["osteoporose", "knochendichte", "lendenwirbelsäule", "frakturrisiko", "osteologie"]
        else: # blood_lab
            pos_kw = ["selbstzahler", "direktlabor", "igel", "ohne überweisung", "wunschlabor", "privatlabor"]
            neg_kw = ["nur kassenpatienten", "überweisungsschein zwingend"]
        
        text_lower = text.lower()
        pos_count = sum(text_lower.count(kw) for kw in pos_kw)
        neg_count = sum(text_lower.count(kw) for kw in neg_kw)
        
        # Keyword Score berechnen
        keyword_score = min(1.0, pos_count / (pos_count + neg_count + 1)) if pos_count > 0 else 0.0

        # 3. Text in sinnvolle Sätze zerlegen
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 30]
        if not sentences: 
            return 0.0, "Text fehlerhaft formatiert."
            
        # Nur die 30 längsten Sätze nehmen, um Rechenzeit zu sparen
        sentences = sorted(sentences, key=len, reverse=True)[:30]
        sentence_embeddings = sbert_model.encode(sentences, convert_to_tensor=True)
        
        # 4. Vergleich mit dem passenden Referenz-Satz
        cosine_scores = util.cos_sim(REF_EMBEDDINGS[category_id], sentence_embeddings)[0]
        max_sbert_score = torch.max(cosine_scores).item()

        # 5. Hybrid Score berechnen (SBERT ist entscheidend, Keywords sind Guardrails)
        final_confidence = (0.7 * max_sbert_score) + (0.3 * keyword_score)
        
        note = f"🤖 KI-Analyse ({category_id}): SBERT: {max_sbert_score:.2f}, Keywords: {keyword_score:.2f}."
        return final_confidence, note

    except requests.exceptions.RequestException:
        return 0.0, "Website offline oder Timeout."
    except Exception as e:
        return 0.0, f"Fehler bei der Website-Analyse: {str(e)}"

def fetch_places(query):
    """Holt die Rohdaten von der Google Places API (New)."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.websiteUri,places.nationalPhoneNumber"
    }
    payload = {"textQuery": query, "languageCode": "de"}
    
    response = requests.post(BASE_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("places", [])
    else:
        print(f"⚠️ API Error ({response.status_code}): {response.text}")
        return []

def main():
    if not API_KEY: 
        print("Error: Bitte GOOGLE_PLACES_API_KEY in der .env setzen.")
        return

    # Unsere Ziel-Städte
    cities = ["Berlin", "Hannover", "München", "Hamburg", "Köln", "Frankfurt", "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Nürnberg"]
    
    # Unser breites Suchnetz (Trichter oben weit aufmachen!)
    categories = [
        {"keyword": "Radiologie DEXA", "id": "dexa"},
        {"keyword": "Orthopädie DEXA", "id": "dexa"},
        {"keyword": "Nuklearmedizin DEXA", "id": "dexa"},
        {"keyword": "Sportmedizin Body Composition", "id": "dexa"},
        {"keyword": "Leistungsdiagnostik Körperfettmessung", "id": "dexa"},
        {"keyword": "Direktlabor Blutuntersuchung Selbstzahler", "id": "blood_lab"}
    ]
    
    all_providers = []
    seen_locations = set()

    print(f"🚀 Starte Enterprise Scraping-Pipeline für {len(cities)} Städte...")
    
    for city in cities:
        print(f"\n📍 Analysiere Region: {city.upper()} " + "="*30)
        for cat in categories:
            query = f"{cat['keyword']} {city}"
            raw_places = fetch_places(query)
            
            if not raw_places: 
                continue
                
            for place in raw_places:
                place_id = place.get('id')
                lat = place.get("location", {}).get("latitude")
                lng = place.get("location", {}).get("longitude")
                
                # GEO-DEDUPLIKATION (ca. 110m Radius)
                if lat and lng:
                    location_key = f"{cat['id']}_{round(lat, 3)}_{round(lng, 3)}"
                else:
                    location_key = f"{cat['id']}_{place_id}"
                
                if location_key in seen_locations:
                    continue
                    
                seen_locations.add(location_key)
                name = place.get("displayName", {}).get("text", "Unbekannter Name")
                website = place.get("websiteUri")
                
                print(f"  🔍 {cat['id'].upper()} | Prüfe: {name[:40]}...")
                
                # KI-Analyse liefert jetzt den rohen Score
                confidence_score, ai_note = analyze_website_text(website, cat['id'])
                
                # Threshold anwenden
                is_ai_verified = confidence_score >= 0.55
                verification_status = "ai_verified" if is_ai_verified else "rejected_by_ai"
                
                if is_ai_verified:
                    print(f"     ✅ KI VERIFIZIERT! ({confidence_score*100:.1f}%)")
                
                entry = {
                    "id": f"{cat['id']}-{place_id}",
                    "name": name,
                    "categories": [cat['id']],
                    "services": {
                        "dexa_body_composition": is_ai_verified if cat['id'] == 'dexa' else False,
                        "blood_test_self_pay": is_ai_verified if cat['id'] == 'blood_lab' else False
                    },
                    "address": {"full_address": place.get("formattedAddress", ""), "city": city, "country": "DE"},
                    "coordinates": {"lat": lat, "lng": lng},
                    "contact": {"phone": place.get("nationalPhoneNumber"), "website": website},
                    "meta": {
                        "ai_confidence_score": round(confidence_score, 3),
                        "verification_status": verification_status,
                        "verified_manually": False, # Der Mensch hat es noch NICHT geprüft!
                        "source": "Google API + Hybrid NLP",
                        "last_updated": datetime.now().isoformat(),
                        "notes": ai_note
                    }
                }
                all_providers.append(entry)

    # --- DATEN SPEICHERN ---
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Haupt-Datenbank (Alle Einträge)
    main_output_path = os.path.join(output_dir, 'data.json')
    with open(main_output_path, 'w', encoding='utf-8') as f:
        json.dump(all_providers, f, indent=2, ensure_ascii=False)
        
    # 2. SPOT-CHECK AUDIT (Die 22 Stichproben für den Menschen)
    high_conf = [p for p in all_providers if p["meta"]["verification_status"] == "ai_verified"]
    low_conf = [p for p in all_providers if p["meta"]["verification_status"] == "rejected_by_ai"]
    
    # Jeweils 11 zufällige (oder weniger, falls nicht genug gefunden)
    audit_sample = random.sample(high_conf, min(11, len(high_conf))) + random.sample(low_conf, min(11, len(low_conf)))
    
    audit_output_path = os.path.join(output_dir, 'audit_samples.json')
    with open(audit_output_path, 'w', encoding='utf-8') as f:
        json.dump(audit_sample, f, indent=2, ensure_ascii=False)

    print(f"\n🎯 MISSION COMPLETE!")
    print(f"Insgesamt {len(all_providers)} Datensätze in 'data/data.json' gespeichert.")
    print(f"📋 AUDIT ERSTELLT: Bitte prüfe die {len(audit_sample)} Einträge in 'data/audit_samples.json' manuell!")

if __name__ == "__main__":
    main()