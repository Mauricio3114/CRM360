from flask import Flask, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_mail import Mail
from flask_socketio import SocketIO
from datetime import datetime

from config import Config

mail = Mail()
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = True

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

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
    from app.models.historico_etapa_lead import HistoricoEtapaLead
    from app.models.lid_mapping import LidMapping
    from app.models.assinatura import Assinatura

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

    @app.before_request
    def bloquear_trial_expirado():
        rotas_liberadas = [
            "auth.login",
            "auth.logout",
            "assinatura.minha_assinatura",
            "assinatura.assinar_agora",
            "asaas_webhook.webhook_asaas",
            "static",
            "contratacao.contratar",
        ]

        if not current_user.is_authenticated:
            return None

        if not current_user.empresa_id:
            return None

        if request.endpoint in rotas_liberadas:
            return None

        assinatura = Assinatura.query.filter_by(
            empresa_id=current_user.empresa_id
        ).order_by(
            Assinatura.id.desc()
        ).first()

        if not assinatura:
            return None

        if assinatura.status == "ativa":
            return None

        if assinatura.trial_ate and datetime.utcnow() > assinatura.trial_ate:
            flash(
                "Seu teste grátis expirou. Assine para continuar usando o MaVa CRM.",
                "warning"
            )

            return redirect(
                url_for("assinatura.minha_assinatura")
            )

        return None

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
    from app.routes.whatsapp_qr import whatsapp_qr_bp
    from app.routes.contratacao import contratacao_bp
    from app.routes.asaas_webhook import asaas_webhook_bp
    from app.routes.assinatura import assinatura_bp
    from app.routes.recuperar_senha import recuperar_senha_bp

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

    from sqlalchemy import text

    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE leads ADD COLUMN valor FLOAT DEFAULT 0"))
        except:
            pass

        try:
            db.session.execute(text("ALTER TABLE leads ADD COLUMN plano VARCHAR(100)"))
        except:
            pass

        try:
            db.session.execute(text("ALTER TABLE leads ADD COLUMN status VARCHAR(30) DEFAULT 'aberto'"))
        except:
            pass

        try:
            db.session.execute(text("ALTER TABLE leads ADD COLUMN criado_em DATETIME"))
        except:
            pass

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
    app.register_blueprint(whatsapp_qr_bp)
    app.register_blueprint(contratacao_bp)
    app.register_blueprint(asaas_webhook_bp)
    app.register_blueprint(assinatura_bp)
    app.register_blueprint(recuperar_senha_bp)

    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    return app