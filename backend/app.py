from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import psycopg2
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from tmdbv3api import TMDb, Discover, Genre
from google_books_api_wrapper.api import GoogleBooksAPI
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
from google import genai
from pydantic import BaseModel

app = Flask(__name__)
CORS(app)

# Initialize the NLP model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize TMDb api
tmdb = TMDb()
tmdb.api_key = '6ad63c632eda943dde42521e2d23749d'

# Initialize google books api
books_client = GoogleBooksAPI()

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

# Initialize gemini LLM for chatbot based recommendations
genai_client = genai.Client(api_key='AIzaSyDlMP6NuRRpb82yyvAaUoRx9TAe6WQrXzU')

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

def fetch_tmdb_movies(search_terms, limit=5):
    """
    Takes a list of search terms from the AI, combines them, 
    and queries the TMDB Search endpoint.
    """
    # 1. Combine our list into a single search query (e.g., "Horror Space Alien")
    query_string = " ".join(search_terms)
    print(f"🎬 Querying TMDB for: '{query_string}'...")
    
    # 2. Hit the /search/movie endpoint
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": tmdb.api_key,
        "query": query_string,
        "language": "en-US",
        "page": 1,
        "include_adult": False # Keep it clean!
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Safely catches 401 Unauthorized or 404 errors
        data = response.json()
        
        results = data.get('results', [])
        
        # 3. TMDB returns relevance first, but we can sort by popularity just to be safe
        sorted_results = sorted(results, key=lambda x: x.get('popularity', 0), reverse=True)
        top_picks = sorted_results[:limit]
        
        # 4. Display the results
        print("\n--- Your Movie Recommendations ---")
        if not top_picks:
            print("No movies found for those terms. Try different keywords!")
            return []
            
        for idx, movie in enumerate(top_picks, start=1):
            title = movie.get('title', 'Unknown Title')
            
            # Safely grab just the year from "YYYY-MM-DD"
            release_date = movie.get('release_date', 'Unknown Date')
            year = release_date.split('-')[0] if release_date else "Unknown Year"
            
            overview = movie.get('overview', 'No description available.')
            short_overview = overview[:150] + "..." if len(overview) > 150 else overview
            
            print(f"{idx}. {title} ({year})")
            print(f"   Description: {short_overview}\n")
            
        return top_picks

    except requests.exceptions.RequestException as e:
        print(f"Error fetching from TMDB: {e}")
        return []

def get_top_rated_books(genres, limit=5):
    all_books = []
    
    for genre in genres:
        result_set = books_client.get_books_by_subject(genre)
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



#  Define our exact JSON structure using Pydantic!
# The new SDK will force the AI to return data that matches this shape perfectly.
class RoutingDecision(BaseModel):
    media_type: str # Instructing it to be 'movie', 'book', or 'music'
    search_terms: list[str]

def analyze_and_route_prompt(user_text):
    print("🧠 AI is analyzing the request (Using modern SDK)...")
    
    # Old prompt (delete later)
    prompt = f"""
    You are an intelligent media recommendation router.
    Read the user's prompt and determine if they are asking for a 'movie', 'book', or 'music'.
    Then, extract 1 to 3 highly relevant search terms, genres, or vibes.
    
    User Prompt: "{user_text}"
    """

    prompt = f"""
    You are an intelligent media recommendation router.
    Read the user's prompt and determine if they are asking for a 'movie', 'book', or 'music'.
    
    If the media is 'movie', you MUST extract 1 to 3 categories strictly from this exact list of official TMDB genres:
    Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Family, Fantasy, History, Horror, Music, Mystery, Romance, Science Fiction, Thriller, War, Western.
    (e.g., if the user asks for "fun and exciting", map it to ["Comedy", "Action"]).
    
    If the media is 'music' or 'book', extract 1 to 3 relevant freeform search terms or vibes.
    
    User Prompt: "{user_text}"
    """
    
    try:
        # 3. Call the new endpoint using the latest Flash model
        response = genai_client.models.generate_content(
            #model='gemini-2.5-flash',
            model = 'gemini-3.1-flash-lite-preview',
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RoutingDecision, # This enforces the strict JSON output!
            )
        )
        
        # The response.text is now GUARANTEED to be a clean JSON string
        return json.loads(response.text)
        
    except Exception as e:
        print(f"Error parsing LLM output: {e}")
        return {"media_type": "unknown", "search_terms": []}


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")

    ai_decision = analyze_and_route_prompt(message)

    media_type = ai_decision.get('media_type')
    search_terms = ai_decision.get('search_terms', [])

    print(f"\n🎯 Detected Category: {media_type.lower()}")
    print(f"🏷️ Extracted Tags: {search_terms}\n")

    # Retrieve suggestions baseed on api
    results = []

    if media_type.lower() == 'book':
        books = get_top_rated_books(search_terms)

        for book in books:
            results.append({
                "title": book.title,
                "type": 'book',
                "description": book.description,
                "score": 1.0
            })

    elif media_type.lower() == 'music':
        music_list = get_music_list(search_terms)

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
                "description": description,
                "score": 1.0
            })

    elif media_type.lower() == 'movie':
        print("Routing to TMDB API...")
        
        # Pass the 'search_terms' list directly to our new function
        movie_picks = fetch_tmdb_movies(search_terms, limit=5)

        for movie in movie_picks:
            # TMDB stores the name under 'title'
            title = movie.get('title', 'Unknown Title')
            
            # TMDB stores the description under 'overview'
            description = movie.get('overview', 'No description available.')
            
            # 3. Append it to your final list in your exact required format
            results.append({
                "title": title,
                "type": 'movie',
                "description": description,
                "score": 1.0
            })
        


    # Return structured JSON instead of a formatted string
    return jsonify({
        "recommendations": results
    })

'''
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
'''


if __name__ == "__main__":
    app.run(port=8000)