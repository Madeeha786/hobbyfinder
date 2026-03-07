from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    database="hobbyfinder",
    user="postgres",
    password="hobbyfinder",
    port=5432
)

cursor = conn.cursor()


def get_recommendations(media_type, genres):
    """
    Query PostgreSQL catalog for matching type and genre
    """
    
    results = []

    for genre in genres:

        cursor.execute(
            """
            SELECT catalog.title, catalog.type, genres.name
            FROM catalog
            JOIN genres ON catalog.genre_id = genres.id
            WHERE catalog.type = %s AND genres.name = %s
            LIMIT 3
            """,
            (media_type, genre)
        )

        '''
        cursor.execute(
            """
            SELECT title, type, genre_id
            FROM catalog
            WHERE type = %s AND genre_id = %s
            LIMIT 3
            """,
            (media_type, genre)
        )
        '''
        
        rows = cursor.fetchall()

        for r in rows:
            results.append({
                "title": r[0],
                "type": r[1],
                "genre": r[2]
            })

    return results

@app.route("/")
def home():
    return "HobbyFinder AI service is running!"

@app.route("/recommend", methods=["POST"])
def recommend():

    data = request.json

    recommendations = []

    # Books
    if "books" in data:
        recs = get_recommendations("book", data["books"])
        recommendations.extend(recs)

    # Movies
    if "movies" in data:
        recs = get_recommendations("movie", data["movies"])
        recommendations.extend(recs)

    # Songs
    if "songs" in data:
        recs = get_recommendations("music", data["songs"])
        recommendations.extend(recs)

    return jsonify({
        "recommendations": recommendations
    })


if __name__ == "__main__":
    app.run(port=8000, debug=True)