from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from . import db

# =======================
# Modelo: Usuario
# =======================
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    clave = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default='vendedor')

    # Relaciones
    ventas = db.relationship('Venta', backref='usuario', lazy=True, cascade="all, delete-orphan")
    ponderaciones = db.relationship('Ponderacion', backref='usuario', lazy=True, cascade="all, delete-orphan")
    metas = db.relationship('Meta', back_populates='usuario', lazy=True, cascade="all, delete-orphan")

# =======================
# Modelo: Venta
# =======================
class Venta(db.Model):
    __tablename__ = 'venta'

    id = db.Column(db.Integer, primary_key=True)
    producto = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(100))
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Relación uno a uno con comisión
    comision = db.relationship('Comision', backref='venta', lazy=True, uselist=False, cascade="all, delete-orphan")

# =======================
# Modelo: Comision
# =======================
class Comision(db.Model):
    __tablename__ = 'comision'

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('venta.id'), nullable=False, unique=True)
    porcentaje = db.Column(db.Float, nullable=False)
    monto = db.Column(db.Float, nullable=False)

# =======================
# Modelo: Ponderacion
# =======================
class Ponderacion(db.Model):
    __tablename__ = 'ponderacion'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(100), nullable=False)  # Ej: 'ventas', 'impactos', etc.
    valor = db.Column(db.Float, nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

# =======================
# Modelo: Meta
# =======================
class Meta(db.Model):
    __tablename__ = 'meta'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)  # Ej: 'ventas', 'impactos', etc.
    valor = db.Column(db.Float, nullable=False)

    usuario = db.relationship('Usuario', back_populates='metas')

# =======================
# Modelo: ResumenComision
# =======================
class ResumenComision(db.Model):
    __tablename__ = 'resumen_comisiones'

    id = db.Column(db.Integer, primary_key=True)
    vendedor = db.Column(db.String, nullable=False)
    categoria = db.Column(db.String, nullable=False)
    ventas = db.Column(db.Float, nullable=False)
    comision = db.Column(db.Float, nullable=False)

# =======================
# Modelo: ImpactoVendedor
# =======================
class ImpactoVendedor(db.Model):
    __tablename__ = 'impactos_vendedor'

    id = db.Column(db.Integer, primary_key=True)
    vendedor = db.Column(db.String, nullable=False)  # correo electrónico
    impactos = db.Column(db.Integer, nullable=False)

# =======================
# Modelo: VentaMarca
# =======================
class VentaMarca(db.Model):
    __tablename__ = 'ventas_marca'

    id = db.Column(db.Integer, primary_key=True)
    vendedor = db.Column(db.String, nullable=False)  # correo electrónico
    marca = db.Column(db.String, nullable=False)     # Ej: 'Finotrato', 'Purina'
    ventas = db.Column(db.Float, nullable=False)
