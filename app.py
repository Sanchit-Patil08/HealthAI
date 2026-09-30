from extensions import db, login_manager, bcrypt
from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from datetime import datetime
import os

login_manager = LoginManager()
bcrypt = Bcrypt()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'healthai-hackathon-secret-2025'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///healthai.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.health_check import health_check_bp
    from routes.medications import medications_bp
    from routes.emergency import emergency_bp
    from routes.profile import profile_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(health_check_bp)
    app.register_blueprint(medications_bp)
    app.register_blueprint(emergency_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Inject 'now' into all templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    with app.app_context():
        import models
        db.create_all()

    return app

from models import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
