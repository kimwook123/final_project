from flask import Blueprint, url_for, request, render_template, g, flash, jsonify
from werkzeug.utils import redirect
from langchain_openai import OpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import AIMessage, HumanMessage  
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.prompts import PromptTemplate
import os
from dotenv import load_dotenv
from openai import OpenAI
import sqlite3
import boto3
import requests
from my_flask_app.models import User, ChatHistory
from flask_login import current_user
from flask import session
from .. import db
from my_flask_app.utils import get_history

MY_BUCKET_NAME = "wooksterbucket"

load_dotenv()  # .env에 작성한 변수를 불러옵니다.

bp = Blueprint('image', __name__, url_prefix='/imagebot')

@bp.route('/get_chat/<int:chat_id>', methods=['GET'])
def get_chat(chat_id):
    try:
        chat_history = ChatHistory.query.get(chat_id)
        if chat_history is None:
            return jsonify({'error': 'Chat not found'}), 404

        # 필요한 데이터만 반환합니다.
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
        chat_histories = ChatHistory.query.filter_by(user_id=current_user.id, type='image').order_by(ChatHistory.created_at.desc()).all()
    else:
        chat_histories = []
    return jsonify({'chat_histories': [{'id': history.id, 'user_question': history.user_question} for history in chat_histories]})

@bp.route('/delete_chat/<int:history_id>', methods=['DELETE'])
def delete_chat(history_id):
    if current_user.is_authenticated:
        chat_history = ChatHistory.query.filter_by(id=history_id, user_id=current_user.id, type='image').first()
        if chat_history:
            db.session.delete(chat_history)
            db.session.commit()
            return jsonify({'success': True})
    return jsonify({'error': '기록을 찾을 수 없습니다.'}), 404

@bp.route('/image', methods=['GET'])
def image_chat_page():
    try:
        if current_user.is_authenticated:
            # 최신 기록이 맨 위에 오도록 내림차순 정렬
            chat_histories = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.created_at.desc()).all()
        else:
            chat_histories = []  # 비로그인 사용자는 빈 리스트 반환
        return render_template('chatbot/image_chatbot.html', chat_histories=chat_histories)
    except Exception as e:
        print("Error fetching chat histories:", str(e))
        return render_template('chatbot/image_chatbot.html', chat_histories=[])

@bp.route('/image', methods=['POST'])
def image():
    try:
        model_id = os.getenv('IMAGE_MODEL_ID')
        model = ImageChatModel(model_id=model_id)
        user_input = request.json.get('message')
        response = model.get_response(user_input)

        save_folder = "./my_flask_app/static/images"
        os.makedirs(save_folder, exist_ok=True)  # 폴더가 없을 때 생성

        img_data = requests.get(response).content

        # user_id 설정
        if current_user.is_authenticated:
            user_id = current_user.id
        else:
            user_id = 'guest'  # 비로그인 사용자를 위한 기본 ID

        counter = 1
        base_filename = f"{user_id}_{counter}.jpg"
        file_path = os.path.join(save_folder, base_filename)

        while os.path.exists(file_path):
            counter += 1
            file_path = os.path.join(save_folder, f"{user_id}_{counter}.jpg")

        with open(file_path, 'wb') as handler:
            handler.write(img_data)
            print("이미지 저장 완료")

        s3_client = boto3.client('s3', region_name='ap-northeast-2')  # S3 클라이언트 설정
        s3_client.upload_file(file_path, MY_BUCKET_NAME, f'{user_id}_{counter}.jpg')

        # S3에 저장한 이미지 URL 생성
        image_url = f"https://{MY_BUCKET_NAME}.s3.ap-northeast-2.amazonaws.com/{user_id}_{counter}.jpg"

        # 데이터베이스에 저장
        if current_user.is_authenticated:
            chat_history = ChatHistory(
                user_id=user_id,
                user_question=user_input,
                maked_text='',
                maked_image_url=image_url,
                type='image'  # 이미지 타입 지정
            )
            db.session.add(chat_history)
            db.session.commit()
            print('DB 저장 완료')

        return jsonify({'response': response})
    
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500

class ImageChatModel:
    def __init__(self, model_id):
        self.graph_builder = StateGraph(MessagesState)
        self.graph_builder.add_node('model', self._call_model)
        self.graph_builder.set_entry_point('model')
        self.memory = MemorySaver()
        self.graph = self.graph_builder.compile(checkpointer=self.memory)
        self.config = {'configurable': {'thread_id': '1'}}

        # 시스템 프롬프트 설정 - 이미지 광고 생성을 위한 역할 지정
        self.system_prompt = {
            "role": "system",
            "content": (
                "너는 텍스트와 이미지 광고를 만드는 AI야. 사용자 요청에 맞는 최신 트렌드 정보를 기반으로 광고용 이미지를 생성해줘. "
                "광고와 무관한 질문에는 '죄송합니다, 저는 광고 작성에만 도움을 드릴 수 있습니다.'라고 답해."
            )
        }

    def _call_model(self, state: MessagesState):
        prompt = PromptTemplate(
            input_variables=["image_desc"],
            template="Generate a detailed prompt to generate an image based on the following description: {image_desc}",
        )
        
        client = OpenAI()

        # 사용자 입력 처리
        if isinstance(state['messages'][0], HumanMessage):  # HumanMessage 객체 확인
            user_message = state['messages'][0].content
        else:
            user_message = state['messages'][0].get('content', '')    

        response = client.images.generate(
            model="dall-e-3",
            prompt=user_message,
        )

        return {'messages': response.data[0].url}
    
    def get_response(self, prompt: str):
        try:
            response = self.graph.invoke({'messages': prompt}, config=self.config)
            print(response)
            for message in response['messages']:
                if isinstance(message, AIMessage):
                    if message.content == "":
                        continue
                    if isinstance(message.content, str):
                        return message.content
                    elif len(message.content) > 0 and message.content[0]['type'] == 'text':
                        return message.content[0]['text']
                elif self.is_image_result(message):
                    return message.content
        except Exception as e:
            print(f"Error invoking the model: {str(e)}")
            return f"Error: {str(e)}"

    def is_image_result(self, message):
        return isinstance(message, HumanMessage) and message.content.startswith('https://')
