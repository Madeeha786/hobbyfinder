from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from tmdbv3api import TMDb, Discover, Genre
from google_books_api_wrapper.api import GoogleBooksAPI
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
CORS(app)

# Initialize the NLP model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize TMDb api
tmdb = TMDb()
tmdb.api_key = '6ad63c632eda943dde42521e2d23749d'

# Initialize google books api
client = GoogleBooksAPI()

# Initialize spotify api
CLIENT_ID = "312081b61b0b4f50b4d60ad2236d111f"
CLIENT_SECRET = "3b89202411184721928d0b2de8f0ed8d"
REDIRECT_URI = "http://127.0.0.1:5500/callback"

SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing" # Scope defines the permissions your app will request

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

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

# Get Genre Ids (FOR MOVIES) based on name
def get_genre_id(genre_name):
    genre = Genre()
    movie_genres = genre.movie_list()
    
    for g in movie_genres:
        if g['name'].lower() == genre_name.lower():
            return g['id']
    return None

def get_top_rated_books(genres, limit=5):
    all_books = []
    
    print(f"Fetching batches from Google Books for: {', '.join(genres)}...")
    for genre in genres:
        result_set = client.get_books_by_subject(genre)
        # Extend our master list with the fetched Book objects
        all_books.extend(result_set.get_all_results())

    # Helper function to safely extract the rating
    def extract_rating(book):
        # We use getattr() to safely pull the rating attribute without throwing errors.
        # Google Books often returns None for unrated books, so we default to 0.0.
        rating = getattr(book, 'average_rating', None) or getattr(book, 'averageRating', 0)
        return float(rating) if rating else 0.0

    # Sort the combined list in descending order (highest rating first)
    sorted_books = sorted(all_books, key=extract_rating, reverse=True)

    # Grab only the top 'limit' amount
    return sorted_books[:limit]

def get_music_list(interests, total_limit=5):
    tracks_by_interest = []
    
    print(f"Fetching bulletproof tracks for: {', '.join(interests)}...")
    
    # Fetch and sort by popularity
    for interest in interests:
        results = sp.search(q=interest, type='track', limit=5)
        tracks = results.get('tracks', {}).get('items', [])
        
        # --- THE FIX: Tag the track with the search vibe so we don't need a second API call later ---
        for track in tracks:
            track['searched_vibe'] = interest
            
        sorted_tracks = sorted(tracks, key=lambda x: x.get('popularity', 0), reverse=True)
        tracks_by_interest.append(sorted_tracks)

    # Round-robin selection
    mixed_picks = []
    for i in range(total_limit): 
        for track_list in tracks_by_interest:
            if len(mixed_picks) >= total_limit:
                break
            if i < len(track_list):
                mixed_picks.append(track_list[i])
        if len(mixed_picks) >= total_limit:
            break

    # Final sort by popularity
    final_top_5 = sorted(mixed_picks, key=lambda x: x.get('popularity', 0), reverse=True)
    return final_top_5


@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.json
    interests_data = data.get("interests", {})
    
    # Fallback just in case the JSON structure differs
    if not interests_data and "movies" in data:
        interests_data = data
        
    catalog = get_catalog()
    results = []

    # Map the JSON keys to the PostgreSQL 'type' column
    category_map = {
        "movies": "movie",
        "books": "book",
        "songs": "music"
    }

    # Add movie suggestions
    movie_interests = interests_data.get("movies", [])
    genre_string = ''
    for genre in movie_interests:
        genre_id = get_genre_id(genre)
        genre_string += '|' + str(genre_id)
    genre_string = genre_string[1:]

    discover = Discover()
    movies = discover.discover_movies({
        'with_genres' : genre_string,
        'sort_by' : 'popularity.desc'
    })

    for movie in list(movies)[:5]:
        results.append({
            "title": movie.title,
            "type": 'movie',
            "score": 1.0,
            "description": movie.overview
        })
    
    # Add book suggestions
    book_interests = interests_data.get("books", [])
    books = get_top_rated_books(book_interests)

    for book in books:
        results.append({
            "title": book.title,
            "type": 'book',
            "score": 1.0,
            "description": book.description
        })
    
    # Add music suggestions
    music_interests = interests_data.get("songs", [])
    music_list = get_music_list(music_interests)

    for track in music_list:
        title = track.get('name', 'Unknown Title')
        artists = ", ".join([artist.get('name') for artist in track.get('artists', [])])
        
        # 1. Extract the Vibe (from the tag we added during the search phase)
        vibe = track.get('searched_vibe', 'an undefinable style')
        
        # 2. Extract Release Year directly from the initial search payload
        release_date = track.get('album', {}).get('release_date', '')
        year = release_date.split('-')[0] if release_date else "an unknown year"
        
        # Put it all together!
        description = f"A popular {vibe} track released in {year} by {artists}."

        results.append({
            "title": title,
            "type": 'music',
            "score": 1.0,
            "description": description
        })


    # Run a dedicated AI search for EACH category the user selected
    '''
    for category_key, db_type in category_map.items():
        cat_interests = interests_data.get(category_key, [])
        
        # If the user didn't pick any genres for this category, skip it
        if not cat_interests:
            continue

        # 1. Filter catalog down to only this specific type
        cat_items = [c for c in catalog if c["type"] == db_type]
        if not cat_items:
            continue

        # 2. Encode user's interests specifically for this type
        user_text = " ".join(cat_interests)
        user_embedding = model.encode([user_text])
        
        # 3. Encode catalog descriptions for this type
        cat_descriptions = [c["description"] for c in cat_items]
        cat_embeddings = model.encode(cat_descriptions)

        #print("Debug info:")
        #print(cat_interests)
        #print([user_text])
        #print([c["description"] for c in cat_items])

        # 4. Calculate similarities
        similarities = cosine_similarity(user_embedding, cat_embeddings)[0]

        ranked = sorted(
            zip(cat_items, similarities),
            key=lambda x: x[1],
            reverse=True
        )

        # 5. Append the top 5 matches for THIS specific category
        for item, score in ranked[:5]:
            results.append({
                "title": item["title"],
                "type": item["type"],
                "score": float(score),
                "description": item["description"]
            })
    '''

    #del results[10:]
    #print(results, flush=True)

    return jsonify({
        "recommendations": results
    })

# ---> THIS WAS THE MISSING FUNCTION <---
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