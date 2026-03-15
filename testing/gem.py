import json
from google import genai
from pydantic import BaseModel

# 1. Initialize the new Client
# (You pass the API key directly to the client now)
client = genai.Client(api_key='AIzaSyDlMP6NuRRpb82yyvAaUoRx9TAe6WQrXzU')

# 2. Define our exact JSON structure using Pydantic!
# The new SDK will force the AI to return data that matches this shape perfectly.
class RoutingDecision(BaseModel):
    media_type: str # Instructing it to be 'movie', 'book', or 'music'
    search_terms: list[str]

def analyze_and_route_prompt(user_text):
    print("🧠 AI is analyzing the request (Using modern SDK)...")
    
    # We no longer need to threaten the AI to format the JSON correctly in the prompt!
    prompt = f"""
    You are an intelligent media recommendation router.
    Read the user's prompt and determine if they are asking for a 'movie', 'book', or 'music'.
    Then, extract 1 to 3 highly relevant search terms, genres, or vibes.
    
    User Prompt: "{user_text}"
    """
    
    try:
        # 3. Call the new endpoint using the latest Flash model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
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

# --- Testing the Upgraded Router ---
user_input = "I need something to read that feels like a cozy mystery set in a small town."
ai_decision = analyze_and_route_prompt(user_input)

media_type = ai_decision.get('media_type')
search_terms = ai_decision.get('search_terms', [])

print(f"\n🎯 Detected Category: {media_type.upper()}")
print(f"🏷️ Extracted Tags: {search_terms}\n")