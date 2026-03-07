from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
CORS(app)

model = SentenceTransformer('all-MiniLM-L6-v2')

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

    for key in data:
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
            "score": float(score)
        })

    return jsonify({
        "recommendations": results
    })


def detect_type(message):

    message = message.lower()

    if "music" in message or "song" in message:
        return "music"

    if "movie" in message or "film" in message:
        return "movie"

    if "book" in message or "novel" in message:
        return "book"

    return None

@app.route("/chat", methods=["POST"])
def chat():

    data = request.json
    message = data["message"]
    media_type = detect_type(message)

    catalog = get_catalog()

    if media_type:
        catalog = [c for c in catalog if c["type"] == media_type]


    descriptions = [c["description"] for c in catalog]

    

    user_embedding = model.encode([message])
    catalog_embeddings = model.encode(descriptions)

    similarities = cosine_similarity(user_embedding, catalog_embeddings)[0]

    ranked = sorted(
        zip(catalog, similarities),
        key=lambda x: x[1],
        reverse=True
    )

    top_items = ranked[:3]

    reply = "Here are some recommendations you might enjoy:\n\n"

    for item, score in top_items:

        reply += f"{item['title']} ({item['type']})\n"
        reply += f"{item['description']}\n\n"

    return jsonify({
        "reply": reply
    })

if __name__ == "__main__":
    app.run(port=8000)