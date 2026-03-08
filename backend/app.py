from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
CORS(app)

# Initialize the NLP model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="hobbyfinder",
    user="postgres",
    password="hobbyfinder"
)

cursor = conn.cursor()

def get_catalog():
    cursor.execute("""
        SELECT title, type, description
        FROM catalog
    """)
    rows = cursor.fetchall()
    catalog = []
    for r in rows:
        catalog.append({
            "title": r[0],
            "type": r[1],
            "description": r[2]
        })
    return catalog

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.json
    interests = []
    
    # Grab user interests from the request body
    if "interests" in data:
        interests_data = data["interests"]
        for key in interests_data:
            interests.extend(interests_data[key])
    else:
        for key in data:
            if isinstance(data[key], list):
                interests.extend(data[key])

    user_text = " ".join(interests)
    catalog = get_catalog()
    catalog_descriptions = [c["description"] for c in catalog]

    user_embedding = model.encode([user_text])
    catalog_embeddings = model.encode(catalog_descriptions)

    similarities = cosine_similarity(user_embedding, catalog_embeddings)[0]

    ranked = sorted(
        zip(catalog, similarities),
        key=lambda x: x[1],
        reverse=True
    )

    results = []
    for item, score in ranked[:5]:
        results.append({
            "title": item["title"],
            "type": item["type"],
            "score": float(score),
            "description": item["description"]
        })

    return jsonify({
        "recommendations": results
    })


def detect_type(message):
    message = message.lower()
    if "music" in message or "song" in message or "track" in message:
        return "music"
    if "movie" in message or "film" in message:
        return "movie"
    if "book" in message or "novel" in message or "read" in message:
        return "book"
    return None

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    media_type = detect_type(message)

    catalog = get_catalog()

    # Filter catalog if the user specifically asked for a book, movie, or music
    if media_type:
        catalog = [c for c in catalog if c["type"] == media_type]

    # Handle edge case where filtering leaves an empty catalog
    if not catalog:
         return jsonify({"recommendations": []})

    descriptions = [c["description"] for c in catalog]

    user_embedding = model.encode([message])
    catalog_embeddings = model.encode(descriptions)

    similarities = cosine_similarity(user_embedding, catalog_embeddings)[0]

    ranked = sorted(
        zip(catalog, similarities),
        key=lambda x: x[1],
        reverse=True
    )

    # Grab the top 3 matches
    top_items = ranked[:3]

    results = []
    for item, score in top_items:
        # We optionally filter out terrible matches (e.g., score < 0.1)
        # but for now, we'll just append the top 3.
        results.append({
            "title": item["title"],
            "type": item["type"],
            "description": item["description"],
            "score": float(score)
        })

    # Return structured JSON instead of a formatted string
    return jsonify({
        "recommendations": results
    })

if __name__ == "__main__":
    app.run(port=8000)