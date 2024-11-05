from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flaskext.markdown import Markdown
from flask_cors import CORS
import config
from flask_login import LoginManager, current_user

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    CORS(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))
    
    # 템플릿에서 current_user를 사용할 수 있도록 설정
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    # ORM 초기화
    db.init_app(app)
    migrate.init_app(app, db)
    from . import models

    # 블루프린트 등록
    from .views import main_views, question_views, answer_views, auth_views, text_chatbot, image_chatbot
    app.register_blueprint(main_views.bp)
    app.register_blueprint(question_views.bp)
    app.register_blueprint(answer_views.bp)
    app.register_blueprint(auth_views.bp)
    app.register_blueprint(text_chatbot.bp)
    app.register_blueprint(image_chatbot.bp)
    
    # 필터
    from .filter import format_datetime
    app.jinja_env.filters['datetime'] = format_datetime

    # markdown
    Markdown(app, extensions=['nl2br', 'fenced_code'])

    return app
