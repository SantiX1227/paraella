import os

# Asegúrate de tener creada la base de datos `miapp_db` desde pgAdmin o con psql
# Reemplaza estos valores según tu entorno
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'
DB_HOST = 'localhost'
DB_NAME = 'Trabajo'

SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'

SECRET_KEY = '1234567'
SQLALCHEMY_TRACK_MODIFICATIONS = False
