from flask import jsonify
from my_flask_app.models import ChatHistory
from flask_login import current_user

def get_history(history_type=None):
    if current_user.is_authenticated:
        # history_type에 따라 필터링하여 채팅 기록을 가져옴
        if history_type:
            chat_histories = ChatHistory.query.filter_by(user_id=current_user.id, type=history_type).all()
        else:
            chat_histories = ChatHistory.query.filter_by(user_id=current_user.id).all()

        history_data = [{'id': history.id, 'user_question': history.user_question} for history in chat_histories]
        return jsonify({'chat_histories': history_data})
    
    return jsonify({'chat_histories': []})
