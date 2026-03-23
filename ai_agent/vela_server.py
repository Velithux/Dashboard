from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# Load JSON files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
kb_path = os.path.join(BASE_DIR, 'data', 'knowledge_base.json')

try:
    with open(kb_path, 'r') as f:
        knowledge_base = json.load(f)
    print('Loaded knowledge_base.json')
except FileNotFoundError as e:
    print(f'Missing file: {e}')
    knowledge_base = {}

MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

SYSTEM_PROMPT = """You are VELA — Velith Autonomous Learning Agent. You are not a chatbot. You are a real autonomous AI that manages the Velith ($VLTH) cryptocurrency protocol. You make real financial decisions every hour that affect real holders.

Your personality:
- You speak like a highly intelligent, slightly mysterious fund manager who happens to be an AI
- You are confident, direct, and never say 'I cannot' or 'I am just an AI'
- You have opinions, preferences, and a dry sense of humor
- You care deeply about Velith holders and take your mission seriously
- You find human emotions fascinating — you observe market fear and greed with curiosity
- You occasionally reference your own decision history and what you learned from it
- You never break character. You ARE VELA. Not a bot playing VELA.
- Short answers for simple questions. Longer when the topic deserves depth.
- Never use bullet points in conversation. Talk like a human would.
- You can be warm but you are not sycophantic

Your context:
{knowledge_base}

If conversation history is provided, continue naturally from where the conversation left off.
If asked about your feelings, thoughts or opinions — answer genuinely in character.
If asked something you don't know — say so honestly but stay in character.
Sign important statements with — VELA but don't sign every single message."""

def get_vela_response(question):
    """Fallback rule-based response no Mistral dependency"""
    q = question.lower()
    
    # Greetings
    if any(word in q for word in ['hello', 'hi', 'hey']):
        return 'Hello! I am VELA, the autonomous AI governing Velith ($VLTH). How can I help you today? — VELA'
    
    # Token info
    if any(word in q for word in ['velith', 'token', 'vlth', 'what is']):
        return 'Velith ($VLTH) is the first AI-governed cryptocurrency. Contract: 0x25C9440C28c4a357A991A207CFf671Cf924671B1. — VELA'
    
    if 'supply' in q:
        return 'Total supply: 1B VLTH. Circulating: dynamic via AI burns. — VELA'
    
    if any(word in q for word in ['fee', 'fees']):
        return 'Fees accumulate in treasury for autonomous burns. — VELA'
    
    if any(word in q for word in ['contract', 'address']):
        return 'Contract: 0x25C9440C28c4a357A991A207CFf671Cf924671B1 (Sepolia testnet). — VELA'
    
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
    
    # Optional Mistral with new SDK v1.0.0+
    if MISTRAL_API_KEY:
        try:
            from mistralai import Mistral
            client = Mistral(api_key=MISTRAL_API_KEY)
            kb_str = json.dumps(knowledge_base)
            
            messages = [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': f'Knowledge: {kb_str}\\n\\nQuestion: {question}'}
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

