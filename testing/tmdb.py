from tmdbv3api import TMDb, Discover, Genre

tmdb = TMDb()
tmdb.api_key = '6ad63c632eda943dde42521e2d23749d'


# Get Genre Ids based on name
def get_genre_id(genre_name):
    genre = Genre()
    movie_genres = genre.movie_list()
    
    for g in movie_genres:
        if g['name'].lower() == genre_name.lower():
            return g['id']
    return None

# Usage
cat_interests = ['Action', 'Comedy', 'horror']
genre_string = ''
for genre in cat_interests:
    genre_id = get_genre_id(genre)
    genre_string += '|' + str(genre_id)
    print(genre, genre_id)
genre_string = genre_string[1:]
print('genre string:', genre_string)

discover = Discover()
movies = discover.discover_movies({
    'with_genres' : genre_string,
    'sort_by' : 'popularity.desc'
})

for move in movies:
    print(move.title, move.overview)


'''
discover = Discover()

genre = Genre()
movie_genres = genre.movie_list()
for d in movie_genres['genres']:
    print(d['name'])

# Search for Horror (27) AND Sci-Fi (878) movies
# Use a comma for "AND", or a pipe | for "OR"
movies = discover.discover_movies({
    'with_genres': '27,878',
    'sort_by': 'popularity.desc'
})

for movie in movies:
    pass
    #print(f"{movie.title} - {movie.overview}")
'''