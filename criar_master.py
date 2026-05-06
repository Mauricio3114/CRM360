from app import create_app, db
from app.models.usuario import Usuario
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    existe = Usuario.query.filter_by(email="master@mavacrm.com").first()

    if existe:
        existe.nome = "Master MaVa"
        existe.tipo = "master"
        existe.senha = generate_password_hash("123456")
        existe.empresa_id = None
        print("Master atualizado:", existe.email)

    else:
        master = Usuario(
            nome="Master MaVa",
            email="master@mavacrm.com",
            senha=generate_password_hash("123456"),
            tipo="master",
            empresa_id=None
        )

        db.session.add(master)

        print("Master criado:", master.email)

    db.session.commit()