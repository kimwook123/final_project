# 아직 미구현
# 이미지 챗봇의 메커니즘은 요청 메뉴얼을 제작하여 AI에게 제공하면,
# AI가 짜여진 프롬프트 메뉴얼에 따라 이미지를 생성하되,
# Tavily 서칭을 활용한 구글링을 통해 최신 트렌드 키워드를 탐색하고,
# 사용자가 제시한 키워드와 트렌드 키워드를 병합하여 이미지를 생성한다.
# 따라서 구글링 후 생성 메커니즘이 텍스트 챗봇 작동방식과 비슷하다.

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

load_dotenv()

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

        return jsonify({'response': list(response)})
    
    except Exception as e:
        print(str(e))
        return jsonify({'error': str(e)}), 500
    
class ImageChatModel:
    def __init__(self, model_id):
        api_key = os.getenv('OPENAI_API_KEY')
        self.imagechat_model = ChatOpenAI(model=model_id)
        self.tool = TavilySearchResults(max_results=3)
        self.tools = [self.tool]
        self.tool_node = ToolNode(tools=self.tools)
        self.imagechat_model_with_tools = self.imagechat_model.bind_tools(self.tools)
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
        return {'messages': self.imagechat_model_with_tools.invoke(state['messages'])}
    
    def get_response(self, prompt: str):
        try:
            response = self.graph.invoke(
                {'messages': prompt},
                config=self.config
            )

            for message in response['messages']:
                if isinstance(message, AIMessage):
                    if isinstance(message.content, str):
                        yield message.content
                    elif len(message.content) > 0 and message.content[0]['type'] == 'text':
                        yield message.content[0]['text']
        except Exception as e:
            print(f"Error invoking the model: {str(e)}")
            yield f"Error: {str(e)}"