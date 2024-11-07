from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import logging

logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__, static_url_path='')
CORS(app)

OLLAMA_API_URL = "http://localhost:11434/api/generate"

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/script.js')
def serve_script():
    return send_from_directory('.', 'script.js')

@app.route('/styles.css')
def serve_styles():
    return send_from_directory('.', 'styles.css')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        print("Received chat request")
        data = request.json
        message = data.get('message')
        print(f"Message: {message}")
        
        print("Calling Ollama API")
        print(f"Ollama URL: {OLLAMA_API_URL}")
        
        try:
            response = requests.post(OLLAMA_API_URL, json={
                "model": "qwen2.5:7b",
                "prompt": message,
                "stream": False
            })
            print(f"Ollama response status: {response.status_code}")
            print(f"Ollama response content: {response.text}")
            
        except requests.exceptions.ConnectionError:
            print("Connection error to Ollama")
            return jsonify({
                "success": False,
                "error": "Cannot connect to Ollama service"
            }), 500
            
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "response": response.json().get('response', '')
            })
        else:
            print(f"Error response from Ollama: {response.text}")
            return jsonify({
                "success": False,
                "error": f"Failed to get response from Ollama: {response.text}"
            }), 500
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000) 