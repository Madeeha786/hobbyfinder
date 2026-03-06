from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/recommend", methods=["POST"])
def recommend():
    interests = request.json["interests"]
    suggestions = []

    for interest in interests:
        if "music" in interest.lower():
            suggestions.append("Learn a musical instrument")
        if "movie" in interest.lower():
            suggestions.append("Explore film making")
        if "book" in interest.lower():
            suggestions.append("Join a book discussion club")
        if "space" in interest.lower():
            suggestions.append("Start astronomy as a hobby")

    if not suggestions:
        suggestions.append("Try creative writing")

    return jsonify({
        "recommendations": list(set(suggestions))
    })

if __name__ == "__main__":
    app.run(port=8000)