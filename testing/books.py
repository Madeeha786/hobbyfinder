'''from google_books_api_wrapper.api import GoogleBooksAPI

books_client = GoogleBooksAPI()

book_interests = ['Fiction', 'Sci Fi']
#books = books_client.get_books_by_subject(book_interests[1])

books = []

for interest in book_interests:
    sub_books = books_client.get_books_by_subject(interest) 
    books.extend(sub_books)

for book in books:
    print(book.title)
    '''

from google_books_api_wrapper.api import GoogleBooksAPI

def get_top_rated_books(genres, limit=5):
    client = GoogleBooksAPI()
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

# Execute the search
book_interests = ['Horror', 'Education']
top_5_picks = get_top_rated_books(book_interests, limit=5)

# Display the final picks
print("\n--- Top 5 Picks ---")
for i, book in enumerate(top_5_picks, start=1):
    authors_list = ", ".join(book.authors) if getattr(book, 'authors', None) else "Unknown"
    
    # Safely get the rating for display purposes
    rating = getattr(book, 'average_rating', None) or getattr(book, 'averageRating', 'No Rating')
    
    print(f"{i}. {book.title}")
    print(f"   Author(s): {authors_list}")
    print(f"   Rating: {rating}/5.0\n")