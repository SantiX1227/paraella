from app import db
from app.models import Usuario
from werkzeug.security import generate_password_hash

def actualizar_contrasenas():
    usuarios = Usuario.query.all()
    for usuario in usuarios:
        if not usuario.clave.startswith('pbkdf2:sha256:'):
            nueva_clave = generate_password_hash(usuario.clave, method='pbkdf2:sha256')
            usuario.clave = nueva_clave

    db.session.commit()
    print("✅ Contraseñas actualizadas exitosamente.")

if __name__ == "__main__":
    from app import create_app
    app = create_app()

    with app.app_context():
        actualizar_contrasenas()
