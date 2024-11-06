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

from my_flask_app.prompts import generate_prompt

load_dotenv()

bp = Blueprint('blog', __name__, url_prefix='/blogbot')

@bp.route('/blog', methods=['GET'])
def blog_chat_page():
    return render_template('chatbot/blog_chatbot.html')


@bp.route('/blog', methods=['POST'])
def blog():
    try:
        options = request.json.get('options')
        prompt = generate_prompt(options)

        model_id = os.getenv('MODEL_ID')
        model = BlogModel(model_id=model_id)
        response = model.get_response(prompt)
        # response = model.get_response('messages')

        if current_user.is_authenticated:
            chat_history = ChatHistory(
                username=current_user.username,
                user_question='', # 프롬프트에서 사용자가 고른 옵션들만 가져와서 저장하기
                maked_text=None,
                maked_image_url=None,  # 이미지를 생성하지 않으면 빈 문자열
                maked_blog_post=response
            )
            db.session.add(chat_history)
            db.session.commit()
            print("데이터베이스에 저장 완료")

        print((response))
        return jsonify({'response': (response)})
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500
    

class BlogModel:
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
                config = self.config
            )

            for message in response['messages']:
                if isinstance(message, AIMessage):
                    continue
                if isinstance(message.content, str):
                    return message.content
                elif len(message.content) > 0 and message.content[0]['type'] == 'text':
                    return message.content[0]['text']
                
        except Exception as e:
            print(f"Error invoking the model: {str(3)}")
            return f"Error: {str(e)}"