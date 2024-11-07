from flask import Blueprint, render_template, url_for
from werkzeug.utils import redirect
from flask_login import current_user
from my_flask_app.models import Question, ChatHistory

bp = Blueprint('main', __name__, url_prefix='/')


@bp.route('/')
def hello_pybo():
    return render_template('index.html')


@bp.route('/')
def index():
    chat_histories = []
    if current_user.is_authenticated:
        chat_histories = ChatHistory.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', chat_histories=chat_histories)


@bp.route('/detail/<int:question_id>/')
def detail(question_id):
    question = Question.query.get(question_id)
    return render_template('question/question_detail.html', question=question)