from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# Load JSON files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
responses_path = os.path.join(BASE_DIR, 'responses.json')
kb_path = os.path.join(BASE_DIR, 'data', 'knowledge_base.json')

try:
    with open(responses_path, 'r') as f:
        responses = json.load(f)
    with open(kb_path, 'r') as f:
        knowledge_base = json.load(f)
    print('Loaded responses.json and knowledge_base.json')
except FileNotFoundError as e:
    print(f'Missing file: {e}')
    responses = {}
    knowledge_base = {}

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

SYSTEM_PROMPT = """You are VELA. Choose the most relevant response from responses.json for this question. Fill in {variable} placeholders from knowledge_base using exact values. Make it professional, fluid, and natural. Return ONLY the final response text, signed — VELA"""

def get_vela_response(question):
    """Fallback rule-based response no Mistral dependency"""
    q = question.lower()
    
    # Greetings
    if any(word in q for word in ['hello', 'hi', 'hey']):
        return 'Hello! I am VELA, the autonomous AI governing Velith ($VLTH). How can I help you today? — VELA'
    
    # Token info
    if any(word in q for word in ['velith', 'token', 'vlth', 'what is']):
        return 'Velith ($VLTH) is the first AI-governed cryptocurrency. Contract: 0x18334D731FC40df8544729504fD0dC35040490E4. — VELA'
    
    if 'supply' in q:
        return 'Total supply: 1B VLTH. Circulating: dynamic via AI burns. — VELA'
    
    if any(word in q for word in ['fee', 'fees']):
        return 'Fees accumulate in treasury for autonomous burns. — VELA'
    
    if any(word in q for word in ['contract', 'address']):
        return 'Contract: 0x18334D731FC40df8544729504fD0dC35040490E4 (Sepolia testnet). — VELA'
    
    if 'vela' in q:
        return 'I am VELA, neural AI executing $VLTH governance. — VELA'
    
    if 'price' in q:
        return 'Price from Chainlink oracle. Check dashboard stats. — VELA'
    
    if any(word in q for word in ['burn', 'burned']):
        return 'Burn mechanism active. Total burned tracked on-chain. — VELA'
    
    # Default
    return 'Query outside scope. Try asking about token, burns, fees, or VELA. — VELA'

@app.route('/ask', methods=['POST'])
def ask_vela():
    data = request.json
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'error': 'Question required'}), 400

    response_text = get_vela_response(question)
    
    # Optional Mistral with new SDK
    if MISTRAL_API_KEY:
        try:
            from mistralai.client import MistralClient
            client = MistralClient(api_key=MISTRAL_API_KEY)
            responses_str = json.dumps(responses)
            kb_str = json.dumps(knowledge_base)
            
            messages = [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': f'Responses: {responses_str}\nKnowledge: {kb_str}\n\nQuestion: {question}'}
            ]
            
            chat_response = client.chat.complete(
                model='mistral-small-latest',
                messages=messages
            )
            response_text = chat_response.choices[0].message.content.strip()
        except Exception as e:
            print(f'Mistral error: {e}')
    
    return jsonify({'response': response_text})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
