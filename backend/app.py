from flask import Flask, request, jsonify
import psycopg2
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

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


if __name__ == "__main__":
    app.run(port=8000)