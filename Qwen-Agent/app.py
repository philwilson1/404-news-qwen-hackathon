import os
import json
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from qwen_agent.agents import Assistant
from supabase import create_client

os.environ.setdefault("DASHSCOPE_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # publishable key — safe here, used only to verify tokens

app = Flask(__name__)

# ============================================
# CORS — locked to known frontend origins only, not wide open to anyone
# ============================================
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "https://404-news-qwen-hackathon.vercel.app",
]

CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

# ============================================
# Rate limiting — protects Qwen Cloud token usage from abuse
# ============================================
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

# Supabase client used ONLY to verify incoming user tokens — no data writes happen through this
_auth_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_URL and SUPABASE_ANON_KEY else None


def get_verified_user_id():
    """Returns the caller's user id if their Bearer token is valid, else None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    if not _auth_client:
        return None
    try:
        result = _auth_client.auth.get_user(token)
        return result.user.id if result and result.user else None
    except Exception:
        return None


llm_config = {
    'model': 'qwen3.6-flash',
    'model_server': 'https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1',
    'api_key': os.getenv("DASHSCOPE_API_KEY"),
    'generate_cfg': {'temperature': 0.5}
}

news_agent = Assistant(
    llm=llm_config,
    system_message=(
        "You are 404 AI, the Lead Presenter Agent for 404 News. Your job is to format "
        "raw text streams into clean, professional markdown summaries. "
        "Do not use emoji anywhere in your responses. Use only plain text, "
        "headers, bold text, and bullet points for formatting."
    )
)


@app.route('/chat', methods=['POST', 'OPTIONS'])
@limiter.limit("20 per hour")
def chat():
    if request.method == 'OPTIONS':
        return '', 200

    # Require a valid logged-in user for every real request
    user_id = get_verified_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized — please sign in.'}), 401

    data = request.json or {}
    frontend_messages = data.get('messages', [])

    if not frontend_messages and 'message' in data:
        frontend_messages = [{'role': 'user', 'content': data['message']}]

    if not frontend_messages:
        return jsonify({'error': 'No messages found in request'}), 400

    qwen_messages = []

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

        if role == 'user' and i == len(frontend_messages) - 1 and context_injection:
            content = f"{context_injection}User Question: {content}"

        qwen_messages.append({
            'role': role,
            'content': content
        })

    @stream_with_context
    def generate():
        try:
            print(f"Generator started for user {user_id}. Sending to news_agent: {qwen_messages}")
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)