import streamlit as st
import sqlite3
from datetime import datetime, date

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="App Ministerio", page_icon="📖", layout="centered")

# --- FUNCIONES DE BASE DE DATOS ---
def inicializar_bd():
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, categoria TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS conversaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, estudiante_id INTEGER, tipo_conversacion TEXT, fecha DATE,
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS actividades_mensuales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, mes TEXT, grupos_realizados INTEGER, grupos_iniciados INTEGER, asistencia_iglesia INTEGER)''')
    conn.commit()
    conn.close()

def obtener_estudiantes():
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, categoria FROM estudiantes ORDER BY nombre ASC")
    datos = cursor.fetchall()
    conn.close()
    return datos

# Inicializar DB al cargar la app
inicializar_bd()

# --- MENÚ LATERAL (SIDEBAR) ---
st.sidebar.title("📖 Ministerio App")
menu = st.sidebar.radio("Navegación", [
    "📊 Dashboard Mensual", 
    "👤 Agregar Estudiante", 
    "💬 Registrar Conversación", 
    "👥 Actividad Grupal"
])

# --- PANTALLA: AGREGAR ESTUDIANTE ---
if menu == "👤 Agregar Estudiante":
    st.header("Agregar Nuevo Estudiante")
    
    with st.form("form_estudiante"):
        nombre = st.text_input("Nombre del estudiante")
        categoria = st.selectbox("Categoría Espiritual", ["Wanderer", "Sojourner", "Explorer", "Follower", "Guia"])
        submit = st.form_submit_button("Guardar Estudiante")
        
        if submit:
            if nombre.strip() == "":
                st.error("El nombre no puede estar vacío.")
            else:
                conn = sqlite3.connect('ministerio.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO estudiantes (nombre, categoria) VALUES (?, ?)", (nombre, categoria))
                conn.commit()
                conn.close()
                st.success(f"¡{nombre} agregado exitosamente como {categoria}!")

# --- PANTALLA: REGISTRAR CONVERSACIÓN ---
elif menu == "💬 Registrar Conversación":
    st.header("Registrar una Conversación")
    
    estudiantes = obtener_estudiantes()
    if not estudiantes:
        st.warning("Primero debes agregar estudiantes en la sección 'Agregar Estudiante'.")
    else:
        # Crear un diccionario para mostrar los nombres pero guardar el ID
        nombres_dict = {f"{est[1]} ({est[2]})": est[0] for est in estudiantes}
        
        with st.form("form_conversacion"):
            estudiante_seleccionado = st.selectbox("Selecciona al estudiante", list(nombres_dict.keys()))
            tipo_conv = st.selectbox("Tipo de conversación", ["1a1", "Conversaciones con Jesus", "Conversaciones intencionales"])
            fecha_conv = st.date_input("Fecha", date.today())
            
            submit_conv = st.form_submit_button("Registrar")
            
            if submit_conv:
                id_estudiante = nombres_dict[estudiante_seleccionado]
                # Convertir la fecha a formato texto para SQLite
                fecha_str = fecha_conv.strftime("%Y-%m-%d")
                
                conn = sqlite3.connect('ministerio.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO conversaciones (estudiante_id, tipo_conversacion, fecha) VALUES (?, ?, ?)", 
                               (id_estudiante, tipo_conv, fecha_str))
                conn.commit()
                conn.close()
                st.success("Conversación registrada exitosamente.")

# --- PANTALLA: ACTIVIDAD GRUPAL ---
elif menu == "👥 Actividad Grupal":
    st.header("Registro de Grupos de Fe e Iglesia")
    st.info("Estos datos se guardan para el mes actual. Si los actualizas, se sobreescribirá la información de este mes.")
    
    mes_actual = date.today().strftime("%Y-%m")
    
    # Buscar si ya hay datos de este mes para mostrarlos por defecto
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT grupos_realizados, grupos_iniciados, asistencia_iglesia FROM actividades_mensuales WHERE mes = ?", (mes_actual,))
    datos_actuales = cursor.fetchone()
    conn.close()
    
    val_realizados = datos_actuales[0] if datos_actuales else 0
    val_iniciados = datos_actuales[1] if datos_actuales else 0
    val_iglesia = datos_actuales[2] if datos_actuales else 0

    with st.form("form_grupos"):
        realizados = st.number_input("Grupos de fe realizados (total del mes)", min_value=0, value=val_realizados)
        iniciados = st.number_input("Nuevos grupos iniciados este mes", min_value=0, value=val_iniciados)
        iglesia = st.number_input("Personas que fueron a la iglesia este mes", min_value=0, value=val_iglesia)
        
        submit_grupos = st.form_submit_button("Guardar Reporte Grupal")
        
        if submit_grupos:
            conn = sqlite3.connect('ministerio.db')
            cursor = conn.cursor()
            if datos_actuales:
                cursor.execute('''UPDATE actividades_mensuales 
                                  SET grupos_realizados=?, grupos_iniciados=?, asistencia_iglesia=? WHERE mes=?''', 
                                  (realizados, iniciados, iglesia, mes_actual))
            else:
                cursor.execute('''INSERT INTO actividades_mensuales (mes, grupos_realizados, grupos_iniciados, asistencia_iglesia) 
                                  VALUES (?, ?, ?, ?)''', (mes_actual, realizados, iniciados, iglesia))
            conn.commit()
            conn.close()
            st.success("Datos grupales actualizados para este mes.")

# --- PANTALLA: DASHBOARD MENSUAL ---
elif menu == "📊 Dashboard Mensual":
    st.header("Dashboard Mensual")
    
    # Seleccionar el mes a visualizar
    meses_opciones = [date.today().strftime("%Y-%m")]
    
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    
    # Obtener todos los meses históricos que tengan registros
    cursor.execute("SELECT DISTINCT strftime('%Y-%m', fecha) FROM conversaciones UNION SELECT mes FROM actividades_mensuales")
    historial = cursor.fetchall()
    for m in historial:
        if m[0] and m[0] not in meses_opciones:
            meses_opciones.append(m[0])
    meses_opciones.sort(reverse=True)
    
    mes_seleccionado = st.selectbox("Selecciona el mes a visualizar:", meses_opciones)
    st.markdown(f"### Resultados de {mes_seleccionado}")
    st.divider()

    # Métrica de Primera Conversación de Jesús (Conteo único)
    cursor.execute('''SELECT COUNT(DISTINCT estudiante_id) FROM conversaciones 
                      WHERE tipo_conversacion = 'Conversaciones con Jesus' AND strftime('%Y-%m', fecha) = ?''', (mes_seleccionado,))
    unicas_jesus = cursor.fetchone()[0]
    
    st.subheader("Métrica Principal")
    st.metric("Primera Conversación de Jesús (Personas Únicas)", unicas_jesus)
    
    # Conversaciones Totales
    st.subheader("Total de Conversaciones Registradas")
    cursor.execute('''SELECT tipo_conversacion, COUNT(*) FROM conversaciones 
                      WHERE strftime('%Y-%m', fecha) = ? GROUP BY tipo_conversacion''', (mes_seleccionado,))
    totales_conv = cursor.fetchall()
    
    if totales_conv:
        col1, col2, col3 = st.columns(3)
        dict_conv = {k:v for k,v in totales_conv}
        col1.metric("1 a 1", dict_conv.get("1a1", 0))
        col2.metric("Con Jesús (Total)", dict_conv.get("Conversaciones con Jesus", 0))
        col3.metric("Intencionales", dict_conv.get("Conversaciones intencionales", 0))
    else:
        st.info("No hay conversaciones registradas este mes.")

    st.divider()
    
    # Actividades Grupales
    st.subheader("Grupos de Fe e Iglesia")
    cursor.execute("SELECT grupos_realizados, grupos_iniciados, asistencia_iglesia FROM actividades_mensuales WHERE mes = ?", (mes_seleccionado,))
    actividades = cursor.fetchone()
    
    if actividades:
        col1, col2, col3 = st.columns(3)
        col1.metric("Grupos Realizados", actividades[0])
        col2.metric("Grupos Iniciados", actividades[1])
        col3.metric("Asistencia a Iglesia", actividades[2])
    else:
        st.info("No hay datos de grupos de fe registrados para este mes.")
        
    conn.close()