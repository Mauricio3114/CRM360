from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    from app.models.usuario import Usuario
    from app.models.empresa import Empresa
    from app.models.lead import Lead
    from app.models.pipeline import Pipeline
    from app.models.interacao import Interacao
    from app.models.tarefa import Tarefa
    from app.models.regra_ia_sdr import RegraIASDR
    from app.models.lancamento_financeiro import LancamentoFinanceiro
    from app.models.meta import Meta
    from app.models.mensagem_whatsapp import MensagemWhatsApp

    @app.context_processor
    def inject_whatsapp_badge():
        total_whatsapp_nao_lidas = 0

        try:
            if current_user.is_authenticated and current_user.empresa_id:
                total_whatsapp_nao_lidas = MensagemWhatsApp.query.filter_by(
                    empresa_id=current_user.empresa_id,
                    direcao="recebida",
                    lida=False
                ).count()
        except Exception:
            total_whatsapp_nao_lidas = 0

        return dict(total_whatsapp_nao_lidas=total_whatsapp_nao_lidas)

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.leads import leads_bp
    from app.routes.pipeline import pipeline_bp
    from app.routes.agenda import agenda_bp
    from app.routes.ia_sdr import ia_sdr_bp
    from app.routes.financeiro import financeiro_bp
    from app.routes.metas import metas_bp
    from app.routes.configuracoes import config_bp
    from app.routes.whatsapp_inbox import whatsapp_inbox_bp
    from app.routes.relatorios import relatorios_bp
    from app.routes.usuarios import usuarios_bp
    from app.routes.master import master_bp

    with app.app_context():
        db.create_all()

    from app.models.usuario import Usuario
    from werkzeug.security import generate_password_hash

    with app.app_context():
        if not Usuario.query.filter_by(email="master@crm360.com").first():
            master = Usuario(
                nome="Master CRM",
                email="master@crm360.com",
                senha=generate_password_hash("123456"),
                tipo="master",
                empresa_id=None
            )
            db.session.add(master)
            db.session.commit()

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(ia_sdr_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(metas_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(whatsapp_inbox_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(master_bp)

    return app