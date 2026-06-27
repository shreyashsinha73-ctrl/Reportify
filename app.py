import os
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

app = Flask(__name__, static_folder='.')
client = genai.Client()

# Define the exact data container we want back from AI Studio
class CivicTicketSchema(BaseModel):
    category: str = Field(description="Must be exactly 'Infrastructure', 'Sanitation', 'Public Safety', or 'Utilities'")
    priority: str = Field(description="Must be exactly 'Low', 'Medium', or 'High'")
    clean_title: str = Field(description="A clean, concise dashboard headline summarizing the event in 4-6 words")

def call_gemini_agent(description: str):
    system_prompt = """
    You are an automated, autonomous Civic Triage Agent working behind the platform 'Reportify'.
    Your objective is to ingest raw citizen descriptions of community infrastructure breakdowns and sort them into clean tracking records.
    """

    # We send the Pydantic schema over to Google AI Studio to handle formatting automatically
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"Analyze this raw submission: {description}",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=CivicTicketSchema, # Enforces structural typing via AI Studio
            temperature=0.1
        )
    )
    
    import json
    return json.loads(response.text)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/report', methods=['POST'])
def process_report():
    payload = request.json
    desc = payload.get('description')
    lat = payload.get('latitude')
    lng = payload.get('longitude')
    
    try:
        # AI Studio guarantees this returns clean, un-wrapped valid JSON dictionary fields
        ai_metrics = call_gemini_agent(desc)
        
        ticket = {
            "title": ai_metrics.get('clean_title'),
            "description": desc,
            "category": ai_metrics.get('category'),
            "priority": ai_metrics.get('priority'),
            "latitude": lat,
            "longitude": lng
        }
        
        print("Structured Agent Output Success:", ticket)
        return jsonify({"success": True, "ticket": ticket}), 201
        
    except Exception as error_context:
        print("Pipeline failure:", error_context)
        return jsonify({"error": str(error_context)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)