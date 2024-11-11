from flask import Blueprint, url_for, request, render_template, g, flash, jsonify
from werkzeug.utils import redirect
from langchain_openai import OpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import AIMessage, HumanMessage  # HumanMessage 추가
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
from .. import db


MY_BUCKET_NAME = "wooksterbucket"

load_dotenv()  # .env에 작성한 변수를 불러온다.

bp = Blueprint('image', __name__, url_prefix='/imagebot')

@bp.route('/image', methods=['GET'])
def image_chat_page():
    return render_template('chatbot/image_chatbot.html')

@bp.route('/image', methods=['POST'])
def image():
    try:
        model_id = os.getenv('IMAGE_MODEL_ID')
        model = ImageChatModel(model_id=model_id)
        user_input = request.json.get('message')
        response = model.get_response(user_input)

        save_folder = "./my_flask_app/static/images"
        os.makedirs(save_folder, exist_ok=True) # 폴더가 없을 때 생성하는 코드인데, 폴더를 만들어 둠

        counter = 1
        base_filename = f"{current_user.username}_{counter}.jpg"
        file_path = os.path.join(save_folder, base_filename)

        while os.path.exists(file_path):
            counter += 1
            file_path = os.path.join(save_folder, f"{current_user.username}_{counter}.jpg")

        img_data = requests.get(response).content
        with open(file_path, 'wb') as handler:
            handler.write(img_data)
            print("이미지 저장 완료")

        s3_client = boto3.client('s3', region_name = 'ap-northeast-2') # 저장 버킷 기본설정
        # bucket 에 생성한 이미지 저장
        s3_client.upload_file(f'./my_flask_app/static/images/{current_user.username}_{counter}.jpg', MY_BUCKET_NAME, f'{current_user.username}_{counter}.jpg')

        # bucket 에 저장한 이미지 url 링크를 받아와야함.
        image_url = f"https://wooksterbucket.s3.ap.northeast-2.amazonaws.com/{current_user.username}_{counter}.jpg"

        # db 저장
        if current_user.is_authenticated:
            chat_history = ChatHistory(
                username=current_user.username,
                user_question=user_input,
                maked_text=None,
                maked_image_url=image_url,
                maked_blog_post=None
            )
            db.session.add(chat_history)
            db.session.commit()
            print('db 저장 완료')

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

        # 사용자 입력과 최신 트렌드를 결합하여 프롬프트 작성
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