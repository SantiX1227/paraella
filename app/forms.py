from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    clave = PasswordField('Clave', validators=[DataRequired()])
    submit = SubmitField('Iniciar sesión')

class RegistroForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    clave = PasswordField('Clave', validators=[DataRequired()])
    confirmar_clave = PasswordField('Confirmar Clave', validators=[
        DataRequired(), EqualTo('clave', message='Las contraseñas deben coincidir')
    ])
    submit = SubmitField('Crear cuenta')
