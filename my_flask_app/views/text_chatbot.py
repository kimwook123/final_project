from datetime import datetime
from flask import Blueprint, url_for, request, render_template, g, flash, jsonify
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

    def get_response(self, prompt: str):
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
                        return message.content.replace("**", "")
                    elif len(message.content) > 0 and message.content[0]['type'] == 'text':
                        return message.content[0]['text'].replace("**", "")
        except Exception as e:
            print(f"Error invoking the model: {str(e)}")
            return f"Error: {str(e)}"

bp = Blueprint('chat', __name__, url_prefix='/chatbot')
model_id = os.getenv('MODEL_ID')
model = ChatModel(model_id=model_id)

@bp.route('/delete_chat/<int:history_id>', methods=['DELETE'])
def delete_chat(history_id):
    if current_user.is_authenticated:
        chat_history = ChatHistory.query.filter_by(id=history_id, user_id=current_user.id).first()
        if chat_history:
            db.session.delete(chat_history)
            db.session.commit()
            return jsonify({'success': True})
    return jsonify({'error': '기록을 찾을 수 없습니다.'}), 404

@bp.route('/get_history', methods=['GET'])
def get_text_history():
    if current_user.is_authenticated:
        chat_histories = ChatHistory.query.filter_by(user_id=current_user.id, type='text').order_by(ChatHistory.created_at.desc()).all()
        print(f"Fetched {len(chat_histories)} chat histories from DB")
        for history in chat_histories:
            print(f"History ID: {history.id}, Question: {history.user_question}")
    else:
        chat_histories = []
    return jsonify({
        'chat_histories': [
            {'id': history.id, 'user_question': history.user_question}
            for history in chat_histories
        ]
    })

@bp.route('/chat', methods=['GET'])
def chat_page():
    if current_user.is_authenticated:
        chat_histories = ChatHistory.query.filter_by(user_id=current_user.id, type='text').order_by(ChatHistory.created_at.desc()).all()
    else:
        chat_histories = []
    return render_template('chatbot/text_chatbot.html', chat_histories=chat_histories)

@bp.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.json.get('message')
        print("Current User:", current_user)
        print("Is Authenticated:", current_user.is_authenticated)
        response = model.get_response(user_input)
        if current_user.is_authenticated:
            chat_history = ChatHistory(
                user_id=current_user.id,
                user_question=user_input,
                maked_text=response,
                maked_image_url='',
                type='text'
            )
            db.session.add(chat_history)
            db.session.commit()
            print("데이터베이스에 질문 저장 완료")
        return jsonify({'response': response})
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500

@bp.route('/get_chat/<int:history_id>', methods=['GET'])
def get_chat(history_id):
    if current_user.is_authenticated:
        chat_history = ChatHistory.query.filter_by(id=history_id, user_id=current_user.id).first()
        if chat_history:
            history_data = {
                'user_question': chat_history.user_question,
                'maked_text': chat_history.maked_text
            }
            return jsonify(history_data), 200
        else:
            return jsonify({'error': '기록을 찾을 수 없습니다.'}), 404
    return jsonify({'error': '인증되지 않았습니다.'}), 403

