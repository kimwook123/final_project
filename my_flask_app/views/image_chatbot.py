from flask import Blueprint, url_for, request, render_template, jsonify
from flask_login import current_user
from .. import db
from my_flask_app.models import ChatHistory
from dotenv import load_dotenv
import os
import requests
import boto3

load_dotenv()  # .env에 작성한 변수를 불러옵니다.

MY_BUCKET_NAME = "wooksterbucket"

bp = Blueprint('image', __name__, url_prefix='/imagebot')

@bp.route('/get_chat/<int:chat_id>', methods=['GET'])
def get_chat(chat_id):
    try:
        chat_history = ChatHistory.query.get(chat_id)
        if chat_history is None:
            return jsonify({'error': 'Chat not found'}), 404

        return jsonify({
            'user_question': chat_history.user_question,
            'maked_text': chat_history.maked_text,
            'maked_image_url': chat_history.maked_image_url
        })
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500

@bp.route('/get_history', methods=['GET'])
def get_image_history():
    if current_user.is_authenticated:
        # 모든 이미지 기록 가져오기
        chat_histories = ChatHistory.query.filter_by(user_id=current_user.id, type='image').order_by(ChatHistory.created_at.desc()).all()
    else:
        chat_histories = []  # 로그인하지 않은 경우 빈 리스트 반환
    return jsonify({'chat_histories': [{'id': history.id, 'user_question': history.user_question} for history in chat_histories]})

@bp.route('/image', methods=['GET'])
def image_chat_page():
    if current_user.is_authenticated:
        chat_histories = ChatHistory.query.filter_by(user_id=current_user.id, type='image').order_by(ChatHistory.created_at.desc()).all()
    else:
        chat_histories = []  # 로그인하지 않은 경우 빈 리스트 반환
    return render_template('chatbot/image_chatbot.html', chat_histories=chat_histories)

@bp.route('/image', methods=['POST'])
def image():
    try:
        user_input = request.json.get('message')
        
        # 모델 응답 생성 로직 (단순화된 형태)
        # 실제로는 model.get_response(user_input) 같은 호출을 통해 이미지를 생성해야 함
        response = "https://example.com/generated_image.jpg"  # 임시로 고정된 URL 사용
        
        # S3에 저장
        save_folder = "./my_flask_app/static/images"
        os.makedirs(save_folder, exist_ok=True)  # 폴더가 없을 때 생성

        # 임시로 응답을 이미지 저장으로 사용
        img_data = requests.get(response).content
        counter = 1
        base_filename = f"{current_user.id}_{counter}.jpg"
        file_path = os.path.join(save_folder, base_filename)

        # 중복 파일이름 방지
        while os.path.exists(file_path):
            counter += 1
            file_path = os.path.join(save_folder, f"{current_user.id}_{counter}.jpg")

        # 파일 저장
        with open(file_path, 'wb') as handler:
            handler.write(img_data)
            print("이미지 저장 완료")

        # S3 업로드
        s3_client = boto3.client('s3', region_name='ap-northeast-2')
        s3_client.upload_file(file_path, MY_BUCKET_NAME, f'{current_user.id}_{counter}.jpg')

        # S3 URL 생성
        image_url = f"https://{MY_BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{current_user.id}_{counter}.jpg"

        # 데이터베이스에 기록 저장
        if current_user.is_authenticated:
            chat_history = ChatHistory(
                user_id=current_user.id,
                user_question=user_input,
                maked_text='',
                maked_image_url=image_url,
                maked_blog_post='',
                type='image'
            )
            db.session.add(chat_history)
            db.session.commit()
            print('DB 저장 완료')

        return jsonify({'response': response})
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500