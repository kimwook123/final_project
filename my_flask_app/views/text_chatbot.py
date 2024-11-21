from datetime import datetime
from flask import Blueprint, url_for, request, render_template, g, flash, jsonify, session
from werkzeug.utils import redirect
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import AIMessage, HumanMessage
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
from my_flask_app.utils import get_history
import uuid

load_dotenv()  # .env에 작성한 변수를 불러온다.

class ChatModel:
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

    def get_response(self, prompt: str, thread_id: str):
        try:
            self.config['configurable']['thread_id'] = thread_id
            response = self.graph.invoke(
                {'messages': prompt},
                config=self.config
            )
            for message in response['messages']:
                if isinstance(message, AIMessage):
                    if message.content == "":
                        continue
                    if isinstance(message.content, str):
                        return message.content.replace("**", "")
                    elif len(message.content) > 0 and message.content[0]['type'] == 'text':
                        return message.content[0]['text'].replace("**", "")
        except Exception as e:
            print(f"Error invoking the model: {str(e)}")
            return f"Error: {str(e)}"

bp = Blueprint('chat', __name__, url_prefix='/chatbot')
model_id = os.getenv('MODEL_ID')
model = ChatModel(model_id=model_id)

@bp.route('/delete_chat/<string:thread_id>', methods=['DELETE'])
def delete_chat(thread_id):
    if current_user.is_authenticated:
        chat_histories = ChatHistory.query.filter_by(thread_id=thread_id, user_id=current_user.id, type='text').all()
        if chat_histories:
            for history in chat_histories:
                db.session.delete(history)
            db.session.commit()
            return jsonify({'success': True})
    return jsonify({'error': '기록을 찾을 수 없습니다.'}), 404

@bp.route('/get_history', methods=['GET'])
def get_text_history():
    if current_user.is_authenticated:
        chat_histories = ChatHistory.query.filter_by(user_id=current_user.id, type='text').order_by(ChatHistory.created_at.desc()).all()
        print(f"Fetched {len(chat_histories)} chat histories from DB")
    else:
        chat_histories = []
    return jsonify({
        'chat_histories': [
            {'thread_id': history.thread_id, 'user_question': history.user_question}
            for history in chat_histories
        ]
    })

@bp.route('/chat', methods=['GET'])
def chat_page():
    try:
        thread_id = request.args.get('thread_id')
        if thread_id:
            # 특정 thread_id의 대화 불러오기
            chat_histories = ChatHistory.query.filter_by(thread_id=thread_id, type='text').order_by(ChatHistory.created_at.asc()).all()
            if not chat_histories:
                flash('해당 대화 기록을 찾을 수 없습니다.', 'error')
                chat_histories = []
        else:
            # 새로운 대화 시작 시 새로운 thread_id 생성
            thread_id = str(uuid.uuid4())
            chat_histories = []
        return render_template('chatbot/text_chatbot.html', chat_histories=chat_histories, thread_id=thread_id)
    except Exception as e:
        print("Error fetching chat histories:", str(e))
        return render_template('chatbot/text_chatbot.html', chat_histories=[], thread_id=str(uuid.uuid4()))

@bp.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.json.get('message')
        thread_id = request.json.get('thread_id')
        if not thread_id:
            thread_id = str(uuid.uuid4())

        response = model.get_response(user_input, thread_id)
        if current_user.is_authenticated:
            chat_history = ChatHistory(
                thread_id=thread_id,
                user_id=current_user.id,
                user_question=user_input,
                maked_text=response,
                maked_image_url='',
                type='text'
            )
            db.session.add(chat_history)
            db.session.commit()
            print("데이터베이스에 질문 저장 완료")
        return jsonify({'response': response, 'thread_id': thread_id})
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500

@bp.route('/get_chat/<string:thread_id>', methods=['GET'])
def get_chat(thread_id):
    if current_user.is_authenticated:
        chat_histories = ChatHistory.query.filter_by(thread_id=thread_id, user_id=current_user.id, type='text').order_by(ChatHistory.created_at.asc()).all()
        if chat_histories:
            history_data = {
                'thread_id': thread_id,
                'chat_history': [
                    {
                        'user_question': history.user_question,
                        'maked_text': history.maked_text,
                        'created_at': history.created_at
                    } for history in chat_histories
                ]
            }
            return jsonify(history_data), 200
        else:
            return jsonify({'error': '기록을 찾을 수 없습니다.'}), 404
    return jsonify({'error': '인증되지 않았습니다.'}), 403
