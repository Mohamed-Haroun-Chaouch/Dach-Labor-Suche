import os
import json
import random
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
import torch

# Initialize environment configurations
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
BASE_URL = "https://places.googleapis.com/v1/places:searchText"

# Load Sentence-BERT model for semantic analysis
# Model: paraphrase-multilingual-MiniLM-L12-v2 (Multi-language support)
print("Initializing AI models...")
sbert_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Define semantic reference embeddings for verification
REF_EMBEDDINGS = {
    "dexa": sbert_model.encode("We provide DEXA scans for body composition, body fat percentage and muscle mass analysis for athletes.", convert_to_tensor=True),
    "blood_lab": sbert_model.encode("We provide blood tests and laboratory analysis for self-paying customers without medical referral.", convert_to_tensor=True)
}

def analyze_website_text(url, category_id):
    """
    Hybrid NLP Classifier utilizing SBERT semantic similarity and keyword density.
    Returns a confidence score between 0.0 and 1.0.
    """
    if not url: 
        return 0.0, "Missing website URL"
        
    try:
        # Fetch website content with a 5-second timeout
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        if len(text) < 100: 
            return 0.0, "Insufficient text for analysis"

        # Define category-specific lexical markers
        if category_id == "dexa":
            pos_kw = ["körperfett", "muskelmasse", "body composition", "sportmedizin", "leistungsdiagnostik", "fettanteil", "zusammensetzung"]
            neg_kw = ["osteoporose", "knochendichte", "lendenwirbelsäule", "frakturrisiko", "osteologie"]
        else:
            pos_kw = ["selbstzahler", "direktlabor", "igel", "ohne überweisung", "wunschlabor", "privatlabor"]
            neg_kw = ["nur kassenpatienten", "überweisungsschein zwingend"]
        
        text_lower = text.lower()
        pos_count = sum(text_lower.count(kw) for kw in pos_kw)
        neg_count = sum(text_lower.count(kw) for kw in neg_kw)
        
        # Calculate lexical score
        keyword_score = min(1.0, pos_count / (pos_count + neg_count + 1)) if pos_count > 0 else 0.0

        # Extract sentences for semantic embedding
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 30]
        if not sentences: 
            return 0.0, "Text parsing error"
            
        sentences = sorted(sentences, key=len, reverse=True)[:30]
        sentence_embeddings = sbert_model.encode(sentences, convert_to_tensor=True)
        
        # Compute cosine similarity against reference embeddings
        cosine_scores = util.cos_sim(REF_EMBEDDINGS[category_id], sentence_embeddings)[0]
        max_sbert_score = torch.max(cosine_scores).item()

        # Weighted ensemble decision logic
        final_confidence = (0.7 * max_sbert_score) + (0.3 * keyword_score)
        
        log_msg = f"Analysis result ({category_id}): SBERT: {max_sbert_score:.2f}, Keywords: {keyword_score:.2f}"
        return final_confidence, log_msg

    except Exception:
        return 0.0, "Analysis failed due to technical error"

def fetch_places(query):
    """Retrieves raw data from Google Places API (New)."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.websiteUri,places.nationalPhoneNumber"
    }
    payload = {"textQuery": query, "languageCode": "de"}
    
    response = requests.post(BASE_URL, headers=headers, json=payload)
    return response.json().get("places", []) if response.status_code == 200 else []

def main():
    if not API_KEY: 
        print("Error: API Key missing")
        return

    cities = ["Berlin", "Hannover", "München", "Hamburg", "Köln", "Frankfurt", "Stuttgart", "Düsseldorf", "Dortmund", "Essen", "Nürnberg"]
    
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

    print(f"Starting enterprise scraping pipeline for {len(cities)} cities...")
    
    for city in cities:
        print(f"Processing Region: {city}")
        for cat in categories:
            query = f"{cat['keyword']} {city}"
            raw_places = fetch_places(query)
            
            for place in raw_places:
                address = place.get("formattedAddress", "")
                if city.lower() not in address.lower():
                    continue
                place_id = place.get('id')
                lat = place.get("location", {}).get("latitude")
                lng = place.get("location", {}).get("longitude")
                
                # Spatial deduplication (approx. 110m radius)
                location_key = f"{cat['id']}_{round(lat, 3)}_{round(lng, 3)}" if lat and lng else place_id
                if location_key in seen_locations: continue
                seen_locations.add(location_key)
                
                website = place.get("websiteUri")
                confidence_score, log_note = analyze_website_text(website, cat['id'])
                
                # Internal threshold for AI verification
                is_ai_verified = confidence_score >= 0.55
                
                entry = {
                    "id": f"{cat['id']}-{place_id}",
                    "name": place.get("displayName", {}).get("text"),
                    "categories": [cat['id']],
                    "services": {
                        "dexa_body_composition": is_ai_verified if cat['id'] == 'dexa' else False,
                        "blood_test_self_pay": is_ai_verified if cat['id'] == 'blood_lab' else False
                    },
                    "address": {"full_address": address, "city": city},
                    "coordinates": {"lat": lat, "lng": lng},
                    "contact": {"phone": place.get("nationalPhoneNumber"), "website": website},
                    "meta": {
                        "ai_confidence_score": round(confidence_score, 3),
                        "verification_status": "ai_verified" if is_ai_verified else "rejected_by_ai",
                        "verified_manually": False,
                        "notes": log_note,
                        "last_updated": datetime.now().isoformat()
                    }
                }
                all_providers.append(entry)

    # Export main database
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, 'data.json'), 'w', encoding='utf-8') as f:
        json.dump(all_providers, f, indent=2, ensure_ascii=False)
        
    # Export audit sample (22 records)
    high_conf = [p for p in all_providers if p["meta"]["verification_status"] == "ai_verified"]
    low_conf = [p for p in all_providers if p["meta"]["verification_status"] == "rejected_by_ai"]
    audit_sample = random.sample(high_conf, min(11, len(high_conf))) + random.sample(low_conf, min(11, len(low_conf)))
    
    with open(os.path.join(output_dir, 'audit_samples.json'), 'w', encoding='utf-8') as f:
        json.dump(audit_sample, f, indent=2, ensure_ascii=False)

    print("Pipeline execution complete.")

if __name__ == "__main__":
    main()