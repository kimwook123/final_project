from datetime import datetime
from flask import Blueprint, url_for, request, render_template, g, flash, jsonify
from werkzeug.utils import redirect
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolNode, tools_condition
import os
from dotenv import load_dotenv
from .. import db
from my_flask_app.forms import UserLoginForm
from my_flask_app.models import User, ChatHistory
from flask_login import current_user
import sqlite3

load_dotenv() # .env에 작성한 변수를 불러온다.

bp = Blueprint('chat', __name__, url_prefix='/chatbot')

@bp.route('/chat', methods=['GET'])
def chat_page():
    return render_template('chatbot/text_chatbot.html')

@bp.route('/chat', methods=['POST'])
def chat():
    try:
        model_id = os.getenv('MODEL_ID')
        model = ChatModel(model_id=model_id)
        user_input = request.json.get('message')

        # current_user 값과 is_authenticated 상태 출력
        print("Current User:", current_user)
        print("Is Authenticated:", current_user.is_authenticated)

        response = model.get_response(user_input)

        if current_user.is_authenticated:
            chat_history = ChatHistory(
                username=current_user.id,
                user_question=user_input,
                maked_text=response,
                maked_image_url='',  # 예: 이미지를 생성하지 않으면 빈 문자열
                maked_blog_post=''   # 예: 블로그 게시물이 없으면 빈 문자열
            )
            db.session.add(chat_history)
            db.session.commit()
            print("데이터베이스에 질문 저장 완료")

        print((response))
        return jsonify({'response': (response)})
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500
    
class ChatModel:
    """Chat 모델 클래스는 주어진 모델 ID로 대화 모델을 초기화하고 요청에 대한 응답을 제공합니다."""
    
    def __init__(self, model_id):
        api_key = os.getenv('OPENAI_API_KEY')
        self.chat_model = ChatOpenAI(model=model_id)
        self.tool = TavilySearchResults(max_results=3)
        self.tools = [self.tool]
        self.tool_node = ToolNode(tools=self.tools)
        self.chat_model_with_tools = self.chat_model.bind_tools(self.tools)
        self.graph_builder = StateGraph(MessagesState)
        self.graph_builder.add_node('model', self._call_model)
        self.graph_builder.add_node('tools', self.tool_node)
        self.graph_builder.set_entry_point('model')
        self.graph_builder.add_conditional_edges(
            'model',
            tools_condition
        )
        self.graph_builder.add_edge('tools', 'model')
        self.memory = MemorySaver()
        self.graph = self.graph_builder.compile(checkpointer=self.memory)
        self.config = {'configurable': {'thread_id': '1'}}

    def _call_model(self, state: MessagesState):
        return {'messages': self.chat_model_with_tools.invoke(state['messages'])}

    def get_response(self, prompt: str):
        """모델에 대한 요청을 보내고 응답을 받는다."""
        try:
            response = self.graph.invoke(
                {'messages': prompt},
                config=self.config
            )

            for message in response['messages']:
                if isinstance(message, AIMessage):
                    if message.content == "":
                        continue
                    if isinstance(message.content, str):
                        return message.content
                    elif len(message.content) > 0 and message.content[0]['type'] == 'text':
                        return message.content[0]['text']
        except Exception as e:
            print(f"Error invoking the model: {str(e)}")
            return f"Error: {str(e)}"