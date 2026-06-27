import os
import json
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_folder='.')

# Set up the Google GenAI Client
# Ensure you run 'export GEMINI_API_KEY="your_key_here"' in your terminal window before starting
client = genai.Client()

def call_gemini_agent(description: str) -> dict:
    """
    Communicates with Google AI Studio using Gemini 1.5 Flash.
    Returns structured operational JSON data back to the application pipeline.
    """
    system_prompt = """
    You are an automated, autonomous Civic Triage Agent working behind the platform 'Reportify'.
    Your objective is to ingest raw citizen descriptions of community infrastructure breakdowns and sort them into clean tracking records.
    
    Categorize the entry strictly into one of the following domains: 'Infrastructure', 'Sanitation', 'Public Safety', or 'Utilities'.
    Assess immediate community danger/risks and assign an urgency Priority evaluation: 'Low', 'Medium', or 'High'.
    Generate a concise, 4-to-6 word summary title suitable for an executive dashboard display.
    
    You must output raw structured JSON text containing only the keys: 'category', 'priority', and 'clean_title'.
    Do not place any markdown format markers like ```json or wrappers around your response text.
    """

    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=f"Analyze this raw submission: {description}",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json"
        )
    )
    
    return json.loads(response.text)

@app.route('/')
def serve_index():
    # Serve our mapping dashboard interface directly from root URL
    return send_from_directory('.', 'index.html')

@app.route('/api/report', methods=['POST'])
def process_report():
    payload = request.json
    desc = payload.get('description')
    lat = payload.get('latitude')
    lng = payload.get('longitude')
    
    if not all([desc, lat, lng]):
        return jsonify({"error": "Malformed report parameters"}), 400
        
    try:
        # Step through the Agent logic via Google AI Studio
        ai_metrics = call_gemini_agent(desc)
        
        ticket = {
            "title": ai_metrics.get('clean_title', 'Civic Ticket Entry'),
            "description": desc,
            "category": ai_metrics.get('category', 'Infrastructure'),
            "priority": ai_metrics.get('priority', 'Medium'),
            "latitude": lat,
            "longitude": lng,
            "status": "Pending"
        }
        
        # In an actual deployment loop, append this ticket to a database storage layer (SQLite/Firestore)
        print("Triage Action Captured:", ticket)
        
        return jsonify({"success": True, "ticket": ticket}), 201
        
    except Exception as error_context:
        print("Agent operational fault:", error_context)
        return jsonify({"error": str(error_context)}), 500

if __name__ == '__main__':
    # Local execution testing parameters
    app.run(host='0.0.0.0', port=5000, debug=True)