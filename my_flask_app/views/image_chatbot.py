from datetime import datetime
from flask import Blueprint, url_for, request, render_template, g, flash, jsonify
from werkzeug.utils import redirect
from langchain_openai import OpenAI
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.prompts import PromptTemplate
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()  # .env에 작성한 변수를 불러온다.

bp = Blueprint('image', __name__, url_prefix='/imagebot')

@bp.route('/image', methods=['GET'])
def image_chat_page():
    return render_template('chatbot/image_chatbot.html')

@bp.route('/image', methods=['POST'])
def image_initialize():
    try:
        model_id = os.getenv('IMAGE_MODEL_ID')
        model = ImageChatModel(model_id=model_id)
        user_input = request.json.get('message')
        response = model.get_response(user_input)
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
        
        # TavilySearch 설정
        self.search_tool = TavilySearchResults(max_results=3)
        
        # OpenAI 클라이언트 설정
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    def _call_model(self, state: MessagesState):
        # TavilySearch를 이용해 최신 트렌드 검색
        search_results = self.search_tool.invoke("latest marketing trends")
        trends = [result.get("title", "No Title") for result in search_results]

        # 사용자 메시지와 최신 트렌드 결합
        user_message = state['messages'][0].content
        prompt_with_trends = f"{user_message}. 최신 트렌드: {', '.join(trends)}."

        # DALL-E 모델에 프롬프트 전달
        response = self.client.images.generate(
            model="dall-e-3",
            prompt=prompt_with_trends,
            size="1024x1024"
        )
        return {'messages': response.data[0].url}

    def get_response(self, prompt: str):
        try:
            response = self.graph.invoke({'messages': prompt}, config=self.config)
            for message in response['messages']:
                if isinstance(message, AIMessage):
                    if isinstance(message.content, str):
                        return message.content
                elif self.is_image_result(message):
                    return message.content
        except Exception as e:
            print(f"Error invoking the model: {str(e)}")
            return f"Error: {str(e)}"

    def is_image_result(self, message):
        return isinstance(message, HumanMessage) and message.content.startswith('https://')
