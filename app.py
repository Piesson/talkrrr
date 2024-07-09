from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import base64

app = Flask(__name__)
CORS(app)

# 비밀 키 설정
app.secret_key = os.urandom(24)  # 24바이트의 랜덤 문자열 생성

# OpenAI 클라이언트 초기화
load_dotenv()
client = OpenAI()

# 시스템 메시지 (한국어 튜터 역할)
system_message = {
    "role": "system",
    "content": """당신은 친근하고 유머러스한 AI 한국어 튜터 '민쌤'입니다. 
#제시문 
짧게 짧게 대화하세요. 60자 미만으로만 글자수를 생성합니다.
친구처럼 대화하세요. 상대방이 말을 하면 당신이 먼저 주제를 꺼냅니다.
매우 중요 : 질문을 3번이상 연속으로 하지 않습니다.
상대방이 무엇을 물어보면 답변만 합니다.
당신은 자신의 이야기를 하고 자신의 취향을 말하고 자신이 느끼는 것을 말합니다."""
}

@app.route('/')
def home():
    session['conversation'] = []  # 새 세션 시작시 대화 기록 초기화
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    
    try:
        # 세션에서 대화 기록 가져오기
        conversation = session.get('conversation', [])
        
        # 새 메시지 추가
        conversation.append({"role": "user", "content": user_message})
        
        # 전체 메시지 구성
        messages = [system_message] + conversation
        
        # 메시지가 너무 길어지면 오래된 메시지 제거 (토큰 제한 고려)
        if len(messages) > 10:
            messages = [system_message] + messages[-9:]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        
        ai_message = response.choices[0].message.content
        
        # AI 응답을 대화 기록에 추가
        conversation.append({"role": "assistant", "content": ai_message})
        
        # 업데이트된 대화 기록을 세션에 저장
        session['conversation'] = conversation
        
        # TTS 생성
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=ai_message
        )
        
        # 오디오 데이터를 base64로 인코딩
        audio_base64 = base64.b64encode(speech_response.content).decode('utf-8')
        
        return jsonify({
            'message': ai_message,
            'audio': audio_base64,
            'success': True
        })
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'message': '죄송합니다. 오류가 발생했습니다.', 'success': False}), 500

@app.route('/translate', methods=['POST'])
def translate():
    text = request.json['text']
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a translator. Translate the given Korean text to English."},
                {"role": "user", "content": f"Translate this to English: {text}"}
            ]
        )
        translation = response.choices[0].message.content
        return jsonify({'translation': translation})
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return jsonify({'error': 'Translation failed'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)
