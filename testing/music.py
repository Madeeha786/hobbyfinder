import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys

# Replace with your Spotify Developer credentials
CLIENT_ID = "312081b61b0b4f50b4d60ad2236d111f"
CLIENT_SECRET = "3b89202411184721928d0b2de8f0ed8d"
REDIRECT_URI = "http://127.0.0.1:5500/callback"

# Scope defines the permissions your app will request
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

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

    print("\n--- Your Top 5 Described Suggestions ---")
    for idx, track in enumerate(final_top_5, start=1):
        title = track.get('name', 'Unknown Title')
        artists = ", ".join([artist.get('name') for artist in track.get('artists', [])])
        
        # 1. Extract the Vibe (from the tag we added during the search phase)
        vibe = track.get('searched_vibe', 'an undefinable style')
        
        # 2. Extract Release Year directly from the initial search payload
        release_date = track.get('album', {}).get('release_date', '')
        year = release_date.split('-')[0] if release_date else "an unknown year"
        
        # Put it all together!
        description = f"A popular {vibe} track released in {year}."

        print(f"{idx}. {title}")
        print(f"   Artist(s): {artists}")
        print(f"   Vibe: {description}\n")

# Execute the search
music_interests = ['Lofi Beats', 'Ambient']
get_music_list(music_interests, total_limit=5)

'''
def get_mixed_top_5(interests, total_limit=5):
    tracks_by_interest = []

    print(f"Fetching and mixing tracks for: {', '.join(interests)}...")

    # 3. Fetch a small batch of tracks for each interest
    for interest in interests:
        results = sp.search(q=interest, type='track', limit=5)
        tracks = results.get('tracks', {}).get('items', [])
        
        # Sort this specific genre's tracks by Spotify's 0-100 popularity score
        sorted_tracks = sorted(tracks, key=lambda x: x.get('popularity', 0), reverse=True)
        tracks_by_interest.append(sorted_tracks)

    # 4. Round-robin selection to guarantee a mix
    mixed_picks = []
    # We loop up to our total_limit to ensure we pull deep enough if needed
    for i in range(total_limit): 
        for track_list in tracks_by_interest:
            # Stop immediately once we hit our exact limit (5)
            if len(mixed_picks) >= total_limit:
                break
            # Safely append the track if it exists
            if i < len(track_list):
                mixed_picks.append(track_list[i])
        
        if len(mixed_picks) >= total_limit:
            break

    # 5. Final sort so the absolute most popular track is #1 on your mixed list
    final_top_5 = sorted(mixed_picks, key=lambda x: x.get('popularity', 0), reverse=True)

    # 6. Display the results
    print("\n--- Your Top 5 Mixed Suggestions ---")
    for idx, track in enumerate(final_top_5, start=1):
        title = track.get('name', 'Unknown Title')
        artists = ", ".join([artist.get('name') for artist in track.get('artists', [])])
        popularity = track.get('popularity', 0)
        
        print(f"{idx}. {title}")
        print(f"   Artist(s): {artists}")
        print(f"   Trending Score: {popularity}/100\n")

# Execute the search
music_interests = ['Lofi Beats', 'Ambient']
get_mixed_top_5(music_interests, total_limit=5)
'''