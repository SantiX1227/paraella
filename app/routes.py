import os
import pandas as pd
import tempfile
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import plotly.express as px
import plotly.io as pio

from .models import db, Usuario, Venta, Comision, Ponderacion, Meta
from .forms import LoginForm, RegistroForm

main = Blueprint('main', __name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'xlsx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

import os
import pandas as pd
import tempfile
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import plotly.express as px
import plotly.io as pio

from .models import db, Usuario, Venta, Ponderacion, Comision
from .forms import LoginForm, RegistroForm

main = Blueprint('main', __name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'xlsx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ======================= LOGIN & REGISTRO =======================

@main.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data).first()
        if usuario and check_password_hash(usuario.clave, form.clave.data):
            login_user(usuario)
            return redirect(url_for('main.dashboard'))
        flash("Credenciales incorrectas.")
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/registro', methods=['GET', 'POST'])
def registro():
    form = RegistroForm()
    if form.validate_on_submit():
        if Usuario.query.filter_by(email=form.email.data).first():
            flash('El correo ya está registrado.')
            return redirect(url_for('main.registro'))
        nuevo_usuario = Usuario(
            nombre=form.nombre.data,
            email=form.email.data,
            clave=generate_password_hash(form.clave.data),
            rol='usuario'
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Cuenta creada exitosamente. ¡Ahora inicia sesión!')
        return redirect(url_for('main.login'))
    return render_template('registro.html', form=form)

# ======================= DASHBOARD =======================

@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', usuario=current_user)

# ======================= CARGAR EXCEL =======================

@main.route('/cargar_excel', methods=['GET', 'POST'])
@login_required
def cargar_excel():
    if request.method == 'POST':
        archivos = request.files.getlist('archivo')
        if not archivos or archivos[0].filename == '':
            flash("No se seleccionaron archivos.")
            return redirect(request.url)

        for archivo in archivos:
            if archivo and allowed_file(archivo.filename):
                original_name = secure_filename(archivo.filename.lower())
                
                if "factura" in original_name:
                    filename = "facturas_ultima.xlsx"
                elif "nota" in original_name:
                    filename = "notas_ultima.xlsx"
                else:
                    filename = original_name  # mantiene su nombre

                filepath = os.path.join(UPLOAD_FOLDER, filename)
                archivo.save(filepath)

                try:
                    df = pd.read_excel(filepath)
                    if "producto" in df.columns and "monto" in df.columns:
                        for _, row in df.iterrows():
                            venta = Venta(
                                producto=row['producto'],
                                marca=row.get('marca'),
                                monto=row['monto'],
                                fecha=pd.to_datetime(row['fecha']).date(),
                                vendedor_id=current_user.id
                            )
                            db.session.add(venta)
                    elif "tipo" in df.columns and "valor" in df.columns:
                        for _, row in df.iterrows():
                            ponderacion = Ponderacion(
                                tipo=row['tipo'],
                                valor=row['valor'],
                                vendedor_id=current_user.id
                            )
                            db.session.add(ponderacion)
                    elif "venta_id" in df.columns and "porcentaje" in df.columns:
                        for _, row in df.iterrows():
                            comision = Comision(
                                venta_id=row['venta_id'],
                                porcentaje=row['porcentaje'],
                                monto=row['monto']
                            )
                            db.session.add(comision)
                    else:
                        flash(f"Archivo {filename} no reconocido. Verifica columnas.")
                except Exception as e:
                    flash(f"Error procesando {filename}: {str(e)}")

        db.session.commit()
        flash("✅ Archivos procesados correctamente.")
        return redirect(url_for('main.reporte'))

    return render_template('cargar_excel.html')


# ======================= REPORTE GENERAL =======================

@main.route('/reporte')
@login_required
def reporte():
    facturas_path = os.path.join(UPLOAD_FOLDER, 'facturas_ultima.xlsx')
    notas_path = os.path.join(UPLOAD_FOLDER, 'notas_ultima.xlsx')

    if not os.path.exists(facturas_path) or not os.path.exists(notas_path):
        flash("❌ Primero debes subir los archivos de facturas y notas de crédito en 'Calcular Comisiones'.")
        return redirect(url_for('main.cargar_excel'))

    facturas = pd.read_excel(facturas_path).fillna(method='ffill')
    notas = pd.read_excel(notas_path).fillna(method='ffill')

    facturas['Usuario'] = facturas['Usuario/Usuario']
    notas['Usuario'] = notas['Usuario/Usuario']
    facturas['Subtotal'] = facturas['Líneas de factura/Subtotal']
    notas['Subtotal'] = notas['Líneas de factura/Subtotal']

    ventas_totales = facturas.groupby('Usuario')['Subtotal'].sum().reset_index(name='Facturas')
    devoluciones = notas.groupby('Usuario')['Subtotal'].sum().reset_index(name='NotasCredito')
    ventas = pd.merge(ventas_totales, devoluciones, on='Usuario', how='left').fillna(0)
    ventas['Ventas Netas'] = ventas['Facturas'] - ventas['NotasCredito']

    clientes = facturas.groupby('Usuario')['Líneas de factura/Asociado'].nunique().reset_index(name='Clientes Influenciados')
    ventas = pd.merge(ventas, clientes, on='Usuario', how='left')
    from .routes import calcular_desempeno_ponderado  # si está en este mismo archivo, no lo repitas
    desempeno_detallado = []

    for correo in ventas['Usuario'].unique():
        usuario = Usuario.query.filter_by(email=correo).first()
        if usuario:
            desempeno = calcular_desempeno_ponderado(usuario, db.session)
            desempeno['Usuario'] = correo
            desempeno_detallado.append(desempeno)

    ventas['Desempeño Ponderado'] = (
        ventas['Ventas Netas'] * 0.5 +
        ventas['Clientes Influenciados'] * 10000
    )

    promedio = ventas['Desempeño Ponderado'].mean()
    ventas['Supera Promedio'] = ventas['Desempeño Ponderado'] > promedio

    # Gráficos principales
    fig1 = px.bar(ventas, x='Usuario', y='Ventas Netas', title='Ventas Totales por Vendedor')
    fig2 = px.bar(ventas, x='Usuario', y='Desempeño Ponderado', title='Desempeño Ponderado por Vendedor')
    fig3 = px.bar(ventas, x='Usuario', y='Clientes Influenciados', title='Clientes Influenciados por Vendedor')
    fig4 = px.bar(ventas, x='Usuario', y='Desempeño Ponderado', color='Supera Promedio',
                  title='¿Quiénes Superan el Desempeño Promedio?', labels={'Supera Promedio': '¿Supera Promedio?'})
    fig5 = px.pie(ventas, names='Usuario', values='Ventas Netas', title='Participación en Ventas Netas')

    # Categoría por vendedor
    cat_fact = facturas.groupby(['Usuario', 'Líneas de factura/Producto/Categoría del Producto'])['Subtotal'].sum().reset_index()
    fig6 = px.bar(cat_fact, y='Usuario', x='Subtotal',
                  color='Líneas de factura/Producto/Categoría del Producto',
                  orientation='h', title='Ventas por Categoría de Producto y Vendedor',
                  height=800)

    # Nuevos gráficos analíticos
    fig7 = px.histogram(ventas, x='Ventas Netas', nbins=10, title='Distribución de Ventas Netas entre Vendedores')
    fig8 = px.box(ventas, y='Desempeño Ponderado', title='Boxplot del Desempeño Ponderado')
    fig9 = px.scatter(ventas, x='Clientes Influenciados', y='Ventas Netas', size='Desempeño Ponderado',
                      hover_name='Usuario', title='Relación entre Clientes Influenciados y Ventas Netas')
    # Clasificación de desempeño ponderado
    promedio = ventas['Desempeño Ponderado'].mean()

    def clasificar(dp, promedio):
        if dp >= promedio * 1.1:
            return 'Destacado'
        elif dp < promedio * 0.75:
            return 'Bajo'
        else:
            return 'Promedio'

    ventas['Clasificación'] = ventas['Desempeño Ponderado'].apply(lambda x: clasificar(x, promedio))

    fig10 = px.bar(
        ventas,
        x='Usuario',
        y='Desempeño Ponderado',
        color='Clasificación',
        title='Clasificación de Vendedores por Desempeño Ponderado',
        color_discrete_map={
            'Destacado': 'green',
            'Promedio': 'gold',
            'Bajo': 'red'
        },
        height=500
    )

    graficos = [
        {
            "id": "ventas",
            "nombre": "Ventas Totales",
            "descripcion": "Este gráfico muestra cuánto vendió cada vendedor después de restar las notas crédito.",
            "div": "grafico_ventas",
            "html": pio.to_html(fig1, full_html=False)
        },
        {
            "id": "desempeno",
            "nombre": "Desempeño",
            "descripcion": "Se calcula combinando las ventas netas y los clientes influenciados.",
            "div": "grafico_ponderado",
            "html": pio.to_html(fig2, full_html=False)
        },
        {
            "id": "clientes",
            "nombre": "Clientes Influenciados",
            "descripcion": "Cantidad de clientes únicos impactados por cada vendedor.",
            "div": "grafico_clientes",
            "html": pio.to_html(fig3, full_html=False)
        },
        {
            "id": "comparativo",
            "nombre": "Comparación con el Promedio",
            "descripcion": "Muestra si un vendedor supera o no el promedio general del desempeño ponderado.",
            "div": "grafico_comparativo",
            "html": pio.to_html(fig4, full_html=False)
        },
        {
            "id": "participacion",
            "nombre": "Participación en Ventas",
            "descripcion": "Distribución porcentual de las ventas netas por vendedor.",
            "div": "grafico_participacion",
            "html": pio.to_html(fig5, full_html=False)
        },
        {
            "id": "categorias",
            "nombre": "Ventas por Categoría",
            "descripcion": "Agrupa las ventas según las categorías de producto vendidas por cada vendedor.",
            "div": "grafico_categoria",
            "html": pio.to_html(fig6, full_html=False)
        },
        {
            "id": "histograma",
            "nombre": "Distribución de Ventas",
            "descripcion": "Histograma que muestra la frecuencia de distintos rangos de ventas netas.",
            "div": "grafico_histograma",
            "html": pio.to_html(fig7, full_html=False)
        },
        {
            "id": "boxplot",
            "nombre": "Boxplot de Desempeño",
            "descripcion": "Visualiza la dispersión y los valores atípicos del desempeño entre vendedores.",
            "div": "grafico_boxplot",
            "html": pio.to_html(fig8, full_html=False)
        },
        {
            "id": "dispersion",
            "nombre": "Clientes vs Ventas",
            "descripcion": "Relaciona visualmente la cantidad de clientes influenciados con las ventas netas.",
            "div": "grafico_dispersion",
            "html": pio.to_html(fig9, full_html=False)
        },
        {
            "id": "clasificacion",
            "nombre": "Clasificación de Desempeño",
            "descripcion": "Indica si un vendedor está por debajo, en promedio o destacado con base en su ponderación.",
            "div": "grafico_clasificacion",
            "html": pio.to_html(fig10, full_html=False)
        }

    ]

    return render_template('reporte.html', usuario=current_user, graficos=graficos, desempeno_detallado=desempeno_detallado)





# ======================= EXPORTAR EXCEL =======================

@main.route('/exportar_excel')
@login_required
def exportar_excel():
    ventas = current_user.ventas
    ponderaciones = current_user.ponderaciones
    comisiones = db.session.query(Comision).join(Venta).filter(Venta.vendedor_id == current_user.id).all()

    df_ventas = pd.DataFrame([{
        'Producto': v.producto,
        'Marca': v.marca,
        'Monto': v.monto,
        'Fecha': v.fecha
    } for v in ventas])

    df_ponderaciones = pd.DataFrame([{
        'Tipo': p.tipo,
        'Valor': p.valor
    } for p in ponderaciones])

    df_comisiones = pd.DataFrame([{
        'Venta ID': c.venta_id,
        'Porcentaje': c.porcentaje,
        'Monto Comisión': c.monto
    } for c in comisiones])

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        with pd.ExcelWriter(tmp.name) as writer:
            df_ventas.to_excel(writer, sheet_name='Ventas', index=False)
            df_comisiones.to_excel(writer, sheet_name='Comisiones', index=False)
            df_ponderaciones.to_excel(writer, sheet_name='Ponderaciones', index=False)
        return send_file(tmp.name, as_attachment=True, download_name="reporte_usuario.xlsx")

# ======================= Cargar y Procesar ============================

@main.route('/calcular_comisiones', methods=['GET', 'POST'])
@login_required
def calcular_comisiones():
    if request.method == 'POST':
        # === 1. Cargar archivos ===
        facturas_file = request.files.get('facturas')
        notas_file = request.files.get('notas')
        porcentaje_file = request.files.get('porcentaje')

        if not all([facturas_file, notas_file, porcentaje_file]):
            flash("❌ Debes subir los tres archivos requeridos.")
            return redirect(request.url)

        facturas_path = os.path.join(UPLOAD_FOLDER, 'facturas_ultima.xlsx')
        notas_path = os.path.join(UPLOAD_FOLDER, 'notas_ultima.xlsx')
        porcentaje_path = os.path.join(UPLOAD_FOLDER, 'porcentaje_ultima.xlsx')

        facturas_file.save(facturas_path)
        notas_file.save(notas_path)
        porcentaje_file.save(porcentaje_path)

        # === 2. Leer archivos Excel ===
        facturas = pd.read_excel(facturas_path).fillna(method='ffill')
        notas = pd.read_excel(notas_path).fillna(method='ffill')
        porcentaje_comision = pd.read_excel(porcentaje_path)


        
        # === 3. Formatear fechas ===
        for df in [facturas, notas]:
            df['Fecha'] = pd.to_datetime(df['Fecha de Factura/Recibo']).dt.strftime('%d/%m/%Y')

        # === 4. Filtrar vendedores ===
        vendedores = [
            'ventas1@grupomulty.com', 'ventas2@grupomulty.com', 'ventas3@grupomulty.com',
            'ventas4@grupomulty.com', 'ventas5@grupomulty.com', 'ventas6@grupomulty.com',
            'ventas7@grupomulty.com', 'analistacomercial@grupomulty.com'
        ]
        facturas = facturas[facturas['Usuario/Usuario'].isin(vendedores)]
        notas = notas[notas['Usuario/Usuario'].isin(vendedores)]

        # === 5. Agrupar subtotales por vendedor y categoría ===
        fact_cat = facturas.groupby(['Usuario/Usuario', 'Líneas de factura/Producto/Categoría del Producto'])[['Líneas de factura/Subtotal']].sum().reset_index()
        notas_cat = notas.groupby(['Usuario/Usuario', 'Líneas de factura/Producto/Categoría del Producto'])[['Líneas de factura/Subtotal']].sum().reset_index()

        fact_cat['clave'] = fact_cat['Usuario/Usuario'] + fact_cat['Líneas de factura/Producto/Categoría del Producto']
        notas_cat['clave'] = notas_cat['Usuario/Usuario'] + notas_cat['Líneas de factura/Producto/Categoría del Producto']

        comision = pd.merge(fact_cat, notas_cat, on='clave', how='left', suffixes=('_facturas', '_notas')).fillna(0)
        comision = comision.rename(columns={
            'Usuario/Usuario_facturas': 'Vendedor',
            'Líneas de factura/Producto/Categoría del Producto_facturas': 'Categoria',
            'Líneas de factura/Subtotal_facturas': 'Facturas',
            'Líneas de factura/Subtotal_notas': 'Notas'
        })
        comision['Ventas Totales'] = (comision['Facturas'] - comision['Notas']).round(0)

        # === 6. Aplicar comisiones ===
        porcentaje_comision.columns = porcentaje_comision.columns.str.strip().str.upper()
        col_categoria = next((col for col in porcentaje_comision.columns if 'nuevo' in col.lower()), None)
        if not col_categoria:
            flash("❌ El archivo de porcentaje de comisión no contiene la columna 'NUEVO'. Verifica el archivo.")
            return redirect(request.url)

        porcentaje_comision = porcentaje_comision.rename(columns={col_categoria: 'Categoria'})
        df_comisiones = pd.merge(comision, porcentaje_comision, on='Categoria', how='left').fillna(0)
        df_comisiones['Comision'] = (df_comisiones['Ventas Totales'] * df_comisiones['COMISION %']).round(0)

        # === 7. Calcular impactos ===
        impactos = facturas.groupby('Usuario/Usuario')['Líneas de factura/Asociado'].nunique().reset_index()
        impactos = impactos.rename(columns={'Usuario/Usuario': 'Vendedor', 'Líneas de factura/Asociado': 'Impactos'})

        # === 8. Calcular ventas por marca ===
        def funcion_marca(df):
            df = df.copy()
            df['marca'] = df['Líneas de factura/Producto'].str.slice(1, 3)
            return df

        facturas = funcion_marca(facturas)
        notas = funcion_marca(notas)

        facturas_marca = facturas.groupby(['Usuario/Usuario', 'marca']).agg({'Líneas de factura/Subtotal': 'sum'}).reset_index()
        notas_marca = notas.groupby(['Usuario/Usuario', 'marca']).agg({'Líneas de factura/Subtotal': 'sum'}).reset_index()

        facturas_marca['clave2'] = facturas_marca['Usuario/Usuario'] + facturas_marca['marca']
        notas_marca['clave2'] = notas_marca['Usuario/Usuario'] + notas_marca['marca']

        ventas_marca = pd.merge(facturas_marca, notas_marca, on='clave2', how='left', suffixes=('_facturas', '_notas')).fillna(0)
        ventas_marca['Ventas Totales'] = (ventas_marca['Líneas de factura/Subtotal_facturas'] - ventas_marca['Líneas de factura/Subtotal_notas']).round(0)
        ventas_marca = ventas_marca.drop(['clave2', 'Líneas de factura/Subtotal_facturas', 'Líneas de factura/Subtotal_notas', 'Usuario/Usuario_notas', 'marca_notas'], axis=1)
        ventas_marca = ventas_marca.rename(columns={'Usuario/Usuario_facturas': 'Vendedor', 'marca_facturas': 'Marca'})

        # === 9. Generar resumen ===
        resumen = df_comisiones.groupby('Vendedor')[['Ventas Totales', 'Comision']].sum().reset_index()
        resumen = resumen.rename(columns={'Ventas Totales': 'VENTA ACTUAL', 'Comision': 'COMISIÓN GENERADA'})
        resumen['CUOTA PARCIAL'] = resumen['VENTA ACTUAL'] * 0.9
        resumen['CONCURSO PAGADO ($)'] = resumen['COMISIÓN GENERADA'] * 0.2
        resumen['EJECUCIÓN (%)'] = (resumen['VENTA ACTUAL'] / resumen['CUOTA PARCIAL']) * 100
        resumen['DESEMPEÑO PONDERADO'] = (
            resumen['VENTA ACTUAL'] * 0.4 +
            resumen['COMISIÓN GENERADA'] * 0.4 +
            resumen['CONCURSO PAGADO ($)'] * 0.2
        )

        # === 10. Incorporar impactos al resumen ===
        resumen = pd.merge(resumen, impactos, on='Vendedor', how='left').fillna(0)

        # === 11. Alertas ===
        promedio_comision = resumen['COMISIÓN GENERADA'].mean()
        alertas_bajo, alertas_alto = [], []
        for _, row in resumen.iterrows():
            alerta = {
                "Vendedor": row['Vendedor'],
                "EJECUCIÓN (%)": round(row['EJECUCIÓN (%)'], 2),
                "VENTA ACTUAL": round(row['VENTA ACTUAL'], 2),
                "CUOTA PARCIAL": round(row['CUOTA PARCIAL'], 2),
                "COMISIÓN GENERADA": round(row['COMISIÓN GENERADA'], 2)
            }
            condiciones_bajo = sum([
                row['EJECUCIÓN (%)'] < 70,
                row['COMISIÓN GENERADA'] < promedio_comision,
                row['VENTA ACTUAL'] < row['CUOTA PARCIAL']
            ])
            condiciones_alto = all([
                row['EJECUCIÓN (%)'] >= 95,
                row['COMISIÓN GENERADA'] >= promedio_comision,
                row['VENTA ACTUAL'] >= row['CUOTA PARCIAL']
            ])
            if condiciones_bajo >= 2:
                alertas_bajo.append(alerta)
            elif condiciones_alto:
                alertas_alto.append(alerta)

        # === 12. Metas y categorías dinámicas ===
        metas_db = Meta.query.all()
        usuarios = {u.id: u.email for u in Usuario.query.all()}
        metas_por_categoria = {}
        for m in metas_db:
            email = usuarios.get(m.usuario_id)
            if email:
                metas_por_categoria.setdefault(email, {})[m.categoria] = m.valor

        # === 13. CATEGORÍAS (incluyendo las nuevas) ===
        categorias = ['ventas', 'impactos', 'Finotrato', 'purina', 'monello', 'kitty paw', 'clientes nuevos']

        # Agregar dinámicamente nuevas categorías si se detectan columnas adicionales en el archivo de porcentaje
        for col in porcentaje_comision.columns:
            col_lower = col.lower()
            if col_lower not in categorias and col_lower != 'categoria' and not col_lower.startswith('comision'):
                categorias.append(col_lower)
                # Guardar la categoría en la base de datos si no existe
                for usuario in Usuario.query.all():
                    existe = Meta.query.filter_by(usuario_id=usuario.id, categoria=col_lower).first()
                    if not existe:
                        nueva_meta = Meta(usuario_id=usuario.id, categoria=col_lower, valor=0.0)
                        db.session.add(nueva_meta)

        db.session.commit()

        # === 14. Cálculo de cumplimiento ===
        for cat in categorias:
            col_meta = f'META {cat.upper()}'
            col_ventas = 'VENTA ACTUAL' if cat == 'ventas' else 'Impactos' if cat == 'impactos' else f'VENTAS {cat.upper()}'
            if col_ventas not in resumen.columns:
                resumen[col_ventas] = 0
            resumen[col_meta] = resumen['Vendedor'].map(lambda x: metas_por_categoria.get(x, {}).get(cat, 0))
            resumen[f'CUMPLIMIENTO {cat.upper()} (%)'] = resumen.apply(
                lambda row: (row[col_ventas] / row[col_meta]) * 100 if row[col_meta] else 0, axis=1
            )

        # === 15. Preparar para renderizado ===
        vendedores_lista = resumen['Vendedor'].tolist()
        resumen_dict = {row['Vendedor']: row for row in resumen.to_dict(orient='records')}
        ponderaciones_dict = {
            v: {
                cat: round(resumen_dict[v].get(f'CUMPLIMIENTO {cat.upper()} (%)', 0), 2)
                for cat in categorias
            }
            for v in vendedores_lista
        }






        flash('✅ Comisiones calculadas con éxito.')
        return render_template(
            'resultado_procesamiento.html',
            alertas_bajo=alertas_bajo,
            alertas_alto=alertas_alto,
            tabla_resumen=resumen.to_dict(orient='records'),
            vendedores=vendedores_lista,
            ponderaciones=ponderaciones_dict,
            resumen_dict=resumen_dict
        )

    return render_template('calcular_comisiones.html')

from app.models import db, Meta, Usuario

@main.route('/agregar_categoria', methods=['POST'])
@login_required
def agregar_categoria():
    nueva_categoria = request.form.get('nueva_categoria')
    if not nueva_categoria:
        flash("❌ No se proporcionó un nombre de categoría.")
        return redirect(url_for('main.calcular_comisiones'))

    usuarios = Usuario.query.all()

    for usuario in usuarios:
        # Verificar si la categoría ya existe para ese usuario
        existe = Meta.query.filter_by(usuario_id=usuario.id, categoria=nueva_categoria).first()
        if not existe:
            nueva_meta = Meta(
                usuario_id=usuario.id,
                categoria=nueva_categoria,
                valor=0.0  # o el valor inicial deseado
            )
            db.session.add(nueva_meta)
    
    db.session.commit()
    flash(f"✅ La categoría '{nueva_categoria}' ha sido creada exitosamente.")
    return redirect(url_for('main.calcular_comisiones'))


CATEGORIAS = ['ventas', 'impactos', 'Finotrato', 'purina', 'monello', 'kitty paw', 'clientes nuevos']

@main.route('/configuraciones', methods=['GET', 'POST'])
@login_required
def configuraciones():

    vendedores_predefinidos = [
        'ventas1@grupomulty.com', 'ventas2@grupomulty.com', 'ventas3@grupomulty.com',
        'ventas4@grupomulty.com', 'ventas5@grupomulty.com', 'ventas6@grupomulty.com',
        'ventas7@grupomulty.com', 'analistacomercial@grupomulty.com'
    ]

    metas_categoria = {v: {cat: 0 for cat in CATEGORIAS} for v in vendedores_predefinidos}

    if request.method == 'POST':
        for correo in vendedores_predefinidos:
            usuario = Usuario.query.filter_by(email=correo).first()
            if not usuario:
                flash(f"❌ No se encontró el usuario {correo}", "danger")
                continue
            for cat in CATEGORIAS:
                field = f"{correo}__{cat}"
                try:
                    valor = float(request.form.get(field, 0))
                    meta = Meta.query.filter_by(usuario_id=usuario.id, categoria=cat).first()
                    if meta:
                        meta.valor = valor
                    else:
                        nueva = Meta(usuario_id=usuario.id, categoria=cat, valor=valor)
                        db.session.add(nueva)
                except Exception as e:
                    flash(f"⚠️ Error con {correo} en {cat}: {e}", "warning")

        db.session.commit()
        flash("✅ Metas guardadas correctamente.", "success")
        return redirect(url_for('main.configuraciones'))

    # === GET: cargar las metas existentes
    for correo in vendedores_predefinidos:
        usuario = Usuario.query.filter_by(email=correo).first()
        if usuario:
            metas = Meta.query.filter_by(usuario_id=usuario.id).all()
            for m in metas:
                if m.categoria in CATEGORIAS:
                    metas_categoria[correo][m.categoria] = m.valor

    # Tabla de ponderaciones (por ahora vacía si no se necesita)
    ponderaciones = {v: {cat: 0 for cat in CATEGORIAS} for v in vendedores_predefinidos}

    return render_template(
        'configuraciones.html',
        vendedores=vendedores_predefinidos,
        categorias=CATEGORIAS,
        metas_categoria=metas_categoria,
        ponderaciones=ponderaciones
    )

from .models import Venta, Ponderacion, Meta, ImpactoVendedor, VentaMarca
from sqlalchemy import func

from .models import Venta, Ponderacion, Meta, ImpactoVendedor, VentaMarca
from sqlalchemy import func

def calcular_desempeno_ponderado(usuario, session):
    vendedor_email = usuario.email

    # === 1. Datos reales por categoría ===
    ventas_totales = session.query(func.sum(Venta.monto))\
        .filter_by(vendedor_id=usuario.id).scalar() or 0

    impactos = session.query(ImpactoVendedor.impactos)\
        .filter_by(vendedor=vendedor_email).scalar() or 0

    ventas_marcas = {
        marca: session.query(func.sum(VentaMarca.ventas))\
            .filter_by(vendedor=vendedor_email, marca=marca).scalar() or 0
        for marca in ['Finotrato', 'purina', 'monello', 'kitty paw']
    }

    clientes_nuevos = 5  # valor fijo, cambia si tienes tabla real

    # === 2. Metas por categoría definidas en Configuraciones ===
    metas = {
        'ventas': session.query(Meta.valor).filter_by(usuario_id=usuario.id).scalar() or 1,
        'impactos': 20,
        'Finotrato': 100000,
        'purina': 80000,
        'monello': 60000,
        'kitty paw': 50000,
        'clientes nuevos': 10
    }

    # === 3. Ponderaciones (% pesos) desde Configuraciones ===
    ponderaciones = {
        p.tipo: p.valor for p in session.query(Ponderacion)
        .filter_by(vendedor_id=usuario.id).all()
    }

    categorias = ['ventas', 'impactos', 'Finotrato', 'purina', 'monello', 'kitty paw', 'clientes nuevos']
    for cat in categorias:
        ponderaciones.setdefault(cat, 0)

    # === 4. Cálculo del desempeño ponderado ===
    valores_reales = {
        'ventas': ventas_totales,
        'impactos': impactos,
        'clientes nuevos': clientes_nuevos,
        **ventas_marcas
    }

    resultado = {}
    total_ponderado = 0

    for cat in categorias:
        valor_real = valores_reales.get(cat, 0)
        meta = metas.get(cat, 1) or 1
        peso = ponderaciones.get(cat, 0)  # ya viene como porcentaje

        cumplimiento_pct = valor_real / meta  # e.g. 0.85
        aporte_ponderado = cumplimiento_pct * (peso / 100)  # e.g. 0.85 * 0.2

        resultado[cat] = {
            'valor_real': round(valor_real, 2),
            'meta': round(meta, 2),
            'cumplimiento': round(cumplimiento_pct * 100, 2),  # porcentaje visible
            'peso': round(peso, 2),
            'ponderado': round(aporte_ponderado * 100, 2)  # también como porcentaje
        }

        total_ponderado += aporte_ponderado

    resultado['total_ponderado'] = round(total_ponderado * 100, 2)  # en %
    resultado['ejecucion'] = resultado['total_ponderado']  # mismo valor
    return resultado

@main.route('/guardar_ponderaciones', methods=['POST'])
@login_required
def guardar_ponderaciones():
    from app.models import Ponderacion, db

    data = request.form
    for key, value in data.items():
        if '__' in key:
            vendedor, campo = key.split('__')
            usuario = Usuario.query.filter_by(email=vendedor).first()
            if usuario:
                ponderacion = Ponderacion.query.filter_by(vendedor_id=usuario.id, tipo=campo).first()
                if not ponderacion:
                    ponderacion = Ponderacion(vendedor_id=usuario.id, tipo=campo)
                ponderacion.valor = float(value)
                db.session.add(ponderacion)

            setattr(ponderacion, campo, float(value))
            db.session.add(ponderacion)

    db.session.commit()
    flash("✅ Ponderaciones actualizadas correctamente.", "success")
    return redirect(url_for('main.calcular_comisiones'))





