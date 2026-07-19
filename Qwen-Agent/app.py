import os
import json
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from qwen_agent.agents import Assistant

os.environ.setdefault("DASHSCOPE_API_KEY", "")

app = Flask(__name__)
CORS(app)

# Remove/delete the old dashscope.base_http_api_url line entirely — not needed here

llm_config = {
    'model': 'qwen3.6-flash',
    'model_server': 'https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1',
    'api_key': os.getenv("DASHSCOPE_API_KEY"),
    'generate_cfg': {'temperature': 0.5}
}


news_agent = Assistant(
    llm=llm_config,
    system_message=(
        "You are the Lead Presenter Agent for 404 News. Your job is to format "
        "raw text streams into clean, professional markdown summaries. "
        "Do not use emoji anywhere in your responses. Use only plain text, "
        "headers, bold text, and bullet points for formatting."
    )
)



# This creates an endpoint at http://127.0.0.1:5000/chat
@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    # Handle the CORS preflight check immediately
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json or {}
    frontend_messages = data.get('messages', [])

    # Fallback in case a raw string 'message' was passed
    if not frontend_messages and 'message' in data:
        frontend_messages = [{'role': 'user', 'content': data['message']}]

    if not frontend_messages:
        return jsonify({'error': 'No messages found in request'}), 400
# Format the messages array to the format Qwen-Agent expects
    qwen_messages = []
    
    # Check if articles are attached in the payload
    attached_articles = data.get('articles', [])
    context_injection = ""
    
    if attached_articles:
        context_injection = "Context references for answering the prompt:\n"
        for art in attached_articles:
            context_injection += f"--- START ARTICLE ARTIFACT ---\nTitle: {art.get('title','')}\nSource: {art.get('source','')}\nSummary: {art.get('summary','')}\n--- END ARTICLE ARTIFACT ---\n\n"

    for i, msg in enumerate(frontend_messages):
        role = msg.get('role', 'user')
        if role not in ('user', 'assistant', 'system'):
            role = 'user'
            
        content = msg.get('content', '')
        
        # Inject context into the final user statement to constrain Qwen's response
        if role == 'user' and i == len(frontend_messages) - 1 and context_injection:
            content = f"{context_injection}User Question: {content}"
            
        qwen_messages.append({
            'role': role,
            'content': content
        })
    

    @stream_with_context
    def generate():
        try:
            print(f"Generator started. Sending to news_agent: {qwen_messages}")
            sent_length = 0

            for response in news_agent.run(messages=qwen_messages):
                if response:
                    last_message = response[-1]

                    if hasattr(last_message, 'content'):
                        full_content = last_message.content
                    elif isinstance(last_message, dict):
                        full_content = last_message.get('content', '')
                    else:
                        full_content = str(last_message)

                    if len(full_content) > sent_length:
                        new_token = full_content[sent_length:]
                        sent_length = len(full_content)

                        chunk = {
                            "choices": [
                                {"delta": {"content": new_token}}
                            ]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            print(f"STREAM ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            error_chunk = {
                "choices": [
                    {"delta": {"content": f"\n\n[Backend Error: {str(e)}]"}}
                ]
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"

    resp = Response(generate(), mimetype='text/event-stream')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['X-Accel-Buffering'] = 'no'
    return resp


if __name__ == '__main__':
    # Run the server locally on port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)