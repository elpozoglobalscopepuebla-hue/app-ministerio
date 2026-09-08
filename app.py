import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- CONFIGURACIÓN DE LA PÁGINA (ESTÉTICA) ---
st.set_page_config(page_title="Ministerio App", page_icon="🌱", layout="wide")

# --- FUNCIONES DE BASE DE DATOS ---
def inicializar_bd():
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    
    # Crear tablas principales
    cursor.execute('''CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, categoria TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS conversaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, estudiante_id INTEGER, tipo_conversacion TEXT, fecha DATE,
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS actividades_mensuales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, mes TEXT, grupos_realizados INTEGER, grupos_iniciados INTEGER, asistencia_iglesia INTEGER)''')
    
    # Actualización automática de la base de datos (agrega la columna 'registrado_por' si no existe)
    try:
        cursor.execute("ALTER TABLE conversaciones ADD COLUMN registrado_por TEXT")
    except sqlite3.OperationalError:
        pass # Si la columna ya existe, simplemente continúa
        
    conn.commit()
    conn.close()

def obtener_estudiantes():
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, categoria FROM estudiantes ORDER BY nombre ASC")
    datos = cursor.fetchall()
    conn.close()
    return datos

# Inicializar DB
inicializar_bd()

# --- ESTILO PERSONALIZADO ---
st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    h1 {color: #1f77b4;}
    h2, h3 {color: #2c3e50;}
    .stAlert {border-radius: 10px;}
    </style>
    """, unsafe_allow_html=True)

# --- MENÚ LATERAL (SIDEBAR) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3256/3256114.png", width=100)
st.sidebar.title("🌱 Ministerio App")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navegación", [
    "📝 Registrar Conversación", 
    "📊 Resumen Mensual",
    "👤 Gestión de Estudiantes", 
    "👥 Actividad Grupal"
])

# --- PANTALLA: REGISTRAR CONVERSACIÓN (REDICEÑADA) ---
if menu == "📝 Registrar Conversación":
    st.title("📝 Registrar Interacciones")
    st.markdown("Selecciona uno o varios estudiantes para registrar la misma interacción de una sola vez.")
    
    estudiantes = obtener_estudiantes()
    if not estudiantes:
        st.warning("Primero debes agregar estudiantes en la sección 'Gestión de Estudiantes'.")
    else:
        nombres_dict = {f"{est[1]} - {est[2]}": est[0] for est in estudiantes}
        
        with st.container(border=True):
            with st.form("form_conversacion"):
                # Uso de columnas para un diseño más limpio
                col1, col2 = st.columns(2)
                
                with col1:
                    usuario_registro = st.text_input("👤 Tu Nombre (Quien registra la conversación)*", placeholder="Ej. David")
                    fecha_conv = st.date_input("📅 Fecha", date.today())
                    
                with col2:
                    tipo_conv = st.selectbox("💬 Tipo de conversación", ["1a1", "Conversaciones con Jesus", "Conversaciones intencionales"])
                    estudiantes_seleccionados = st.multiselect("👥 Selecciona a los estudiantes (puedes elegir varios)*", list(nombres_dict.keys()))
                
                st.markdown("---")
                submit_conv = st.form_submit_button("Guardar Registros", use_container_width=True)
                
                if submit_conv:
                    if not usuario_registro.strip():
                        st.error("Por favor, ingresa tu nombre.")
                    elif not estudiantes_seleccionados:
                        st.error("Por favor, selecciona al menos un estudiante.")
                    else:
                        fecha_str = fecha_conv.strftime("%Y-%m-%d")
                        conn = sqlite3.connect('ministerio.db')
                        cursor = conn.cursor()
                        
                        # Registrar una conversación por cada estudiante seleccionado
                        for est_nombre in estudiantes_seleccionados:
                            id_estudiante = nombres_dict[est_nombre]
                            cursor.execute("INSERT INTO conversaciones (estudiante_id, tipo_conversacion, fecha, registrado_por) VALUES (?, ?, ?, ?)", 
                                           (id_estudiante, tipo_conv, fecha_str, usuario_registro.strip()))
                        
                        conn.commit()
                        conn.close()
                        st.toast('¡Conversaciones registradas con éxito!', icon='✅')
                        st.success(f"Se registraron {len(estudiantes_seleccionados)} interacciones por {usuario_registro}.")

# --- PANTALLA: DASHBOARD MENSUAL (MEJORADA) ---
elif menu == "📊 Resumen Mensual":
    st.title("📊 Resumen Mes a Mes")
    
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    
    # Obtener historial de meses
    cursor.execute("SELECT DISTINCT strftime('%Y-%m', fecha) FROM conversaciones UNION SELECT mes FROM actividades_mensuales")
    historial = [m[0] for m in cursor.fetchall() if m[0]]
    if not historial:
        historial = [date.today().strftime("%Y-%m")]
    historial.sort(reverse=True)
    
    # Selector de mes intuitivo
    mes_seleccionado = st.selectbox("📅 Selecciona el mes a analizar:", historial)
    
    st.markdown("---")
    
    # METRICAS CLAVE
    cursor.execute('''SELECT COUNT(DISTINCT estudiante_id) FROM conversaciones 
                      WHERE tipo_conversacion = 'Conversaciones con Jesus' AND strftime('%Y-%m', fecha) = ?''', (mes_seleccionado,))
    unicas_jesus = cursor.fetchone()[0]
    
    col1, col2 = st.columns([1, 2])
    with col1:
        with st.container(border=True):
            st.metric("🌟 Conversaciones con Jesús (Únicas)", unicas_jesus, help="Cuenta solo 1 vez por estudiante al mes.")
            
    with col2:
        cursor.execute('''SELECT tipo_conversacion, COUNT(*) FROM conversaciones 
                          WHERE strftime('%Y-%m', fecha) = ? GROUP BY tipo_conversacion''', (mes_seleccionado,))
        totales_conv = {k:v for k,v in cursor.fetchall()}
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total 1 a 1", totales_conv.get("1a1", 0))
        c2.metric("Con Jesús (Total)", totales_conv.get("Conversaciones con Jesus", 0))
        c3.metric("Intencionales", totales_conv.get("Conversaciones intencionales", 0))

    st.markdown("### 👥 Desglose de Actividad por Miembro del Equipo")
    # Tabla de quién registró qué
    query = f"""
        SELECT registrado_por as 'Líder', tipo_conversacion as 'Tipo', COUNT(*) as 'Cantidad'
        FROM conversaciones 
        WHERE strftime('%Y-%m', fecha) = '{mes_seleccionado}' AND registrado_por IS NOT NULL
        GROUP BY registrado_por, tipo_conversacion
    """
    df_lideres = pd.read_sql_query(query, conn)
    
    if not df_lideres.empty:
        # Reorganizar la tabla para que sea más fácil de leer
        df_pivot = df_lideres.pivot(index='Líder', columns='Tipo', values='Cantidad').fillna(0).astype(int)
        st.dataframe(df_pivot, use_container_width=True)
    else:
        st.info("No hay registros con nombres de líderes para este mes.")

    # Registro en crudo
    with st.expander("Ver todas las interacciones del mes (Historial)"):
        query_historial = f"""
            SELECT c.fecha as 'Fecha', c.registrado_por as 'Registró', e.nombre as 'Estudiante', e.categoria as 'Categoría', c.tipo_conversacion as 'Interacción'
            FROM conversaciones c
            JOIN estudiantes e ON c.estudiante_id = e.id
            WHERE strftime('%Y-%m', c.fecha) = '{mes_seleccionado}'
            ORDER BY c.fecha DESC
        """
        df_historial = pd.read_sql_query(query_historial, conn)
        st.dataframe(df_historial, use_container_width=True, hide_index=True)

    conn.close()

# --- PANTALLA: GESTIÓN DE ESTUDIANTES ---
elif menu == "👤 Gestión de Estudiantes":
    st.title("👤 Base de Datos de Estudiantes")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Agregar Nuevo")
        with st.form("form_estudiante"):
            nombre = st.text_input("Nombre completo")
            categoria = st.selectbox("Categoría Espiritual", ["Wanderer", "Sojourner", "Explorer", "Follower", "Guia"])
            submit = st.form_submit_button("Guardar Estudiante", use_container_width=True)
            
            if submit:
                if nombre.strip():
                    conn = sqlite3.connect('ministerio.db')
                    conn.execute("INSERT INTO estudiantes (nombre, categoria) VALUES (?, ?)", (nombre.strip(), categoria))
                    conn.commit()
                    conn.close()
                    st.success(f"Agregado: {nombre}")
                else:
                    st.error("El nombre es requerido.")

    with col2:
        st.subheader("Directorio Actual")
        conn = sqlite3.connect('ministerio.db')
        df_est = pd.read_sql_query("SELECT nombre as 'Nombre', categoria as 'Categoría' FROM estudiantes ORDER BY nombre", conn)
        conn.close()
        
        if not df_est.empty:
            st.dataframe(df_est, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay estudiantes registrados.")

# --- PANTALLA: ACTIVIDAD GRUPAL ---
elif menu == "👥 Actividad Grupal":
    st.title("👥 Grupos de Fe e Iglesia")
    st.markdown("Registra las métricas grupales del mes. Si actualizas estos números, **reemplazarán** los datos anteriores de este mismo mes.")
    
    mes_actual = date.today().strftime("%Y-%m")
    
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT grupos_realizados, grupos_iniciados, asistencia_iglesia FROM actividades_mensuales WHERE mes = ?", (mes_actual,))
    datos = cursor.fetchone()
    
    with st.container(border=True):
        with st.form("form_grupos"):
            st.subheader(f"Métricas para: {mes_actual}")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                realizados = st.number_input("Grupos de fe realizados", min_value=0, value=datos[0] if datos else 0)
            with c2:
                iniciados = st.number_input("Nuevos grupos iniciados", min_value=0, value=datos[1] if datos else 0)
            with c3:
                iglesia = st.number_input("Asistencia a la iglesia", min_value=0, value=datos[2] if datos else 0)
            
            st.markdown("---")
            if st.form_submit_button("Guardar Reporte Grupal", use_container_width=True):
                if datos:
                    cursor.execute("UPDATE actividades_mensuales SET grupos_realizados=?, grupos_iniciados=?, asistencia_iglesia=? WHERE mes=?", 
                                      (realizados, iniciados, iglesia, mes_actual))
                else:
                    cursor.execute("INSERT INTO actividades_mensuales (mes, grupos_realizados, grupos_iniciados, asistencia_iglesia) VALUES (?, ?, ?, ?)", 
                                      (mes_actual, realizados, iniciados, iglesia))
                conn.commit()
                st.success("Métricas grupales actualizadas con éxito.")
    conn.close()
