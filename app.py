import streamlit as st
import pandas as pd
from datetime import datetime, date
import psycopg2
from sqlalchemy import create_engine

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ministerio App", page_icon="🌱", layout="wide")

# --- CONEXIÓN A SUPABASE (POSTGRESQL) ---
try:
    # Lee el secreto de Streamlit y asegura que empiece con postgresql://
    DB_URL = st.secrets["conexiones"]["url_base"].replace("postgres://", "postgresql://")
except:
    st.error("⚠️ No se encontró el enlace de conexión en los Secrets de Streamlit. Ve a Settings > Secrets y agrega tu url_base.")
    st.stop()

# Engine para leer tablas fácilmente con Pandas
engine = create_engine(DB_URL)

def get_connection():
    return psycopg2.connect(DB_URL)

# --- INICIALIZACIÓN DE BASE DE DATOS EN LA NUBE ---
def inicializar_bd():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS estudiantes (
        id SERIAL PRIMARY KEY, 
        nombre TEXT NOT NULL, 
        categoria TEXT NOT NULL,
        estado TEXT DEFAULT 'Activo',
        telefono TEXT DEFAULT 'Sin dato',
        escuela TEXT DEFAULT 'Sin dato',
        edad TEXT DEFAULT 'Sin dato',
        cumpleanos TEXT DEFAULT 'Sin dato'
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS conversaciones (
        id SERIAL PRIMARY KEY, 
        estudiante_id INTEGER, 
        tipo_conversacion TEXT, 
        fecha DATE,
        registrado_por TEXT,
        nombre_visitante TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reportes_grupales (
        semana_str TEXT PRIMARY KEY, 
        mes_pertenencia TEXT, 
        grupos_realizados INTEGER, 
        grupos_iniciados INTEGER, 
        nombres_iglesia TEXT, 
        registrado_por TEXT
    )''')
    
    conn.commit()
    conn.close()

inicializar_bd()

def obtener_semana_actual():
    hoy = date.today()
    num_semana = hoy.isocalendar()[1]
    return f"{hoy.year}-W{num_semana:02d}", hoy.strftime("%Y-%m")

if 'alertas_registro' not in st.session_state:
    st.session_state['alertas_registro'] = []

# --- ESTILO ---
st.markdown("""
    <style>
    .main {background-color: #f4f6f9;}
    h1, h2, h3 {color: #2c3e50;}
    </style>
    """, unsafe_allow_html=True)

# --- MENÚ LATERAL ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3256/3256114.png", width=80)
st.sidebar.title("🌱 Ministerio")
menu = st.sidebar.radio("Navegación", [
    "📝 Súper Registro (Diario/Semanal)", 
    "📊 Resumen Mensual",
    "👤 Directorio Estudiantes", 
    "⚙️ Administración Avanzada"
])

# =====================================================================
# 1. SÚPER FORMULARIO
# =====================================================================
if menu == "📝 Súper Registro (Diario/Semanal)":
    st.title("📝 Registro Integral")
    
    if st.session_state['alertas_registro']:
        visitante = st.session_state['alertas_registro'][0]
        st.warning(f"🔔 **¡Atención!** El visitante **{visitante}** ha acumulado 3 (o más) interacciones. ¿Deseas agregarlo oficialmente?")
        col_y, col_n = st.columns([1, 4])
        with col_y:
            with st.popover("Sí, registrar ahora"):
                st.write(f"Registrando a: {visitante}")
                cat = st.selectbox("Categoría*", ["Wanderer", "Sojourner", "Explorer", "Follower", "Guia"])
                if st.button("Guardar Oficialmente"):
                    conn = get_connection()
                    c = conn.cursor()
                    # En PostgreSQL se usa RETURNING id para obtener el ID recién creado
                    c.execute("INSERT INTO estudiantes (nombre, categoria) VALUES (%s, %s) RETURNING id", (visitante, cat))
                    nuevo_id = c.fetchone()[0]
                    c.execute("UPDATE conversaciones SET estudiante_id = %s, nombre_visitante = NULL WHERE nombre_visitante = %s", (nuevo_id, visitante))
                    conn.commit()
                    conn.close()
                    st.session_state['alertas_registro'].pop(0)
                    st.success("¡Registrado con éxito!")
                    st.rerun()
        with col_n:
            if st.button("No por ahora"):
                st.session_state['alertas_registro'].pop(0)
                st.rerun()
        st.markdown("---")

    estudiantes_activos = pd.read_sql_query("SELECT id, nombre, categoria FROM estudiantes WHERE estado = 'Activo' ORDER BY nombre", engine)
    nombres_dict = {f"{row['nombre']} ({row['categoria']})": row['id'] for _, row in estudiantes_activos.iterrows()}
    
    semana_actual, mes_actual = obtener_semana_actual()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT grupos_realizados, nombres_iglesia, grupos_iniciados FROM reportes_grupales WHERE semana_str = %s", (semana_actual,))
    datos_sem = c.fetchone()
    conn.close()

    with st.form("form_super_registro", clear_on_submit=True):
        st.markdown("### 👤 1. Datos del Staff")
        col1, col2 = st.columns(2)
        with col1: usuario = st.text_input("Tu Nombre (Quien registra)*", value="") 
        with col2: fecha_conv = st.date_input("📅 Fecha de interacciones", date.today())
        
        st.markdown("---")
        st.markdown("### 💬 2. Registro de Conversaciones")
        st.write("Agrega a los estudiantes oficiales en el selector, o escribe a los visitantes separados por coma.")
        
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.markdown("#### 🗣️ 1 a 1")
            est_1a1 = st.multiselect("Oficiales:", list(nombres_dict.keys()), key="m1")
            vis_1a1 = st.text_input("Visitantes (separados por coma):", key="v1")
        with c2: 
            st.markdown("#### 🌟 Con Jesús")
            est_jesus = st.multiselect("Oficiales:", list(nombres_dict.keys()), key="m2")
            vis_jesus = st.text_input("Visitantes (separados por coma):", key="v2")
        with c3: 
            st.markdown("#### 🎯 Intencionales")
            est_intencionales = st.multiselect("Oficiales:", list(nombres_dict.keys()), key="m3")
            vis_intencionales = st.text_input("Visitantes (separados por coma):", key="v3")

        st.markdown("---")
        st.markdown("### 📅 3. Reporte de la Semana Pasada")
        st.info("Solo llena esto si te toca reportar tus grupitos. Si no tuviste, déjalo en cero.")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            r = st.number_input("¿Cuantos grupitos basados en la fe tuviste la semana pasada?", min_value=0, value=0)
            i = st.number_input("¿Cuantos grupitos basados en la fe se arrancaron la semana pasada?", min_value=0, value=0)
        with col_r2:
            n = st.text_area("¿Quien llevaste a la iglesia la semana pasada? (Nombres)", value="")

        st.markdown("---")
        submit = st.form_submit_button("🚀 Guardar Todo el Reporte", use_container_width=True, type="primary")
        
        if submit:
            if not usuario.strip(): 
                st.error("Debes ingresar tu nombre en la Sección 1.")
            else:
                conn = get_connection()
                c = conn.cursor()
                fecha_str = fecha_conv.strftime("%Y-%m-%d")
                staff = usuario.strip()
                
                def guardar_visitantes(texto_visitantes, tipo):
                    if not texto_visitantes.strip(): return
                    nombres = [nom.strip() for nom in texto_visitantes.split(",") if nom.strip()]
                    for nom in nombres:
                        c.execute("INSERT INTO conversaciones (nombre_visitante, tipo_conversacion, fecha, registrado_por) VALUES (%s, %s, %s, %s)", (nom, tipo, fecha_str, staff))
                        c.execute("SELECT COUNT(*) FROM conversaciones WHERE nombre_visitante = %s", (nom,))
                        if c.fetchone()[0] % 3 == 0:
                            if nom not in st.session_state['alertas_registro']:
                                st.session_state['alertas_registro'].append(nom)

                for est in est_1a1: c.execute("INSERT INTO conversaciones (estudiante_id, tipo_conversacion, fecha, registrado_por) VALUES (%s, %s, %s, %s)", (nombres_dict[est], "1a1", fecha_str, staff))
                for est in est_jesus: c.execute("INSERT INTO conversaciones (estudiante_id, tipo_conversacion, fecha, registrado_por) VALUES (%s, %s, %s, %s)", (nombres_dict[est], "Conversaciones con Jesus", fecha_str, staff))
                for est in est_intencionales: c.execute("INSERT INTO conversaciones (estudiante_id, tipo_conversacion, fecha, registrado_por) VALUES (%s, %s, %s, %s)", (nombres_dict[est], "Conversaciones intencionales", fecha_str, staff))
                
                guardar_visitantes(vis_1a1, "1a1")
                guardar_visitantes(vis_jesus, "Conversaciones con Jesus")
                guardar_visitantes(vis_intencionales, "Conversaciones intencionales")

                if r > 0 or i > 0 or n.strip():
                    c.execute("SELECT semana_str FROM reportes_grupales WHERE semana_str = %s", (semana_actual,))
                    if c.fetchone():
                        c.execute("UPDATE reportes_grupales SET grupos_realizados=%s, grupos_iniciados=%s, nombres_iglesia=%s, registrado_por=%s WHERE semana_str=%s", (r, i, n, staff, semana_actual))
                    else:
                        c.execute("INSERT INTO reportes_grupales (semana_str, mes_pertenencia, grupos_realizados, grupos_iniciados, nombres_iglesia, registrado_por) VALUES (%s, %s, %s, %s, %s, %s)", (semana_actual, mes_actual, r, i, n, staff))
                
                conn.commit()
                conn.close()
                st.success('✅ ¡Registro guardado exitosamente en la nube! Las casillas han sido limpiadas.')
                if st.session_state['alertas_registro']: st.rerun()

# =====================================================================
# 2. RESUMEN MENSUAL Y EXPORTACIÓN
# =====================================================================
elif menu == "📊 Resumen Mensual":
    st.title("📊 Resumen Mes a Mes")
    
    # En PostgreSQL extraemos año y mes con TO_CHAR
    query_meses = "SELECT DISTINCT TO_CHAR(fecha, 'YYYY-MM') as mes FROM conversaciones UNION SELECT mes_pertenencia as mes FROM reportes_grupales"
    meses_df = pd.read_sql_query(query_meses, engine)
    historial = [m for m in meses_df['mes'].dropna().tolist()]
    if not historial: historial = [date.today().strftime("%Y-%m")]
    historial.sort(reverse=True)
    
    col_sel, col_btn = st.columns([2, 1])
    with col_sel:
        mes_sel = st.selectbox("📅 Selecciona el mes a analizar:", historial)
    st.divider()

    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM conversaciones WHERE tipo_conversacion = '1a1' AND TO_CHAR(fecha, 'YYYY-MM') = %s", (mes_sel,))
    tot_1a1 = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM conversaciones WHERE tipo_conversacion = 'Conversaciones intencionales' AND TO_CHAR(fecha, 'YYYY-MM') = %s", (mes_sel,))
    tot_int = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM conversaciones WHERE tipo_conversacion = 'Conversaciones con Jesus' AND TO_CHAR(fecha, 'YYYY-MM') = %s", (mes_sel,))
    tot_jesus = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT COALESCE(estudiante_id::text, nombre_visitante)) FROM conversaciones WHERE tipo_conversacion = 'Conversaciones con Jesus' AND TO_CHAR(fecha, 'YYYY-MM') = %s", (mes_sel,))
    unicas_jesus = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(grupos_realizados), 0), COALESCE(SUM(grupos_iniciados), 0) FROM reportes_grupales WHERE mes_pertenencia = %s", (mes_sel,))
    sumas_grupales = c.fetchone()

    st.success(f"📖 **Resumen Explicativo:** Durante el mes de **{mes_sel}**, el equipo sostuvo un total de **{tot_1a1}** conversaciones 1 a 1, **{tot_int}** pláticas intencionales, y **{tot_jesus}** conversaciones sobre Jesús. Este esfuerzo espiritual logró alcanzar a **{unicas_jesus}** personas únicas con el mensaje de Jesús. En el aspecto comunitario, el Staff sumó **{sumas_grupales[0]}** grupitos de fe realizados y se logró arrancar **{sumas_grupales[1]}** grupos nuevos.")

    st.markdown("#### 🗣️ Esfuerzo de Interacciones")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total 1 a 1", tot_1a1)
    c2.metric("Total Intencionales", tot_int)
    c3.metric("Total Con Jesús", tot_jesus)
    c4.metric("🌟 Únicas Con Jesús", unicas_jesus)
    
    st.markdown("#### 👥 Esfuerzo Comunitario")
    g1, g2, g3 = st.columns([1, 1, 2])
    g1.metric("Grupos Realizados", sumas_grupales[0])
    g2.metric("Nuevos Grupos Iniciados", sumas_grupales[1])

    st.markdown("---")
    st.markdown("### 📋 Historial Detallado de Conversaciones")
    query_historial = f"""
        SELECT c.fecha as "Fecha", 
               COALESCE(e.nombre, c.nombre_visitante) as "Persona", 
               CASE WHEN e.nombre IS NOT NULL THEN 'Oficial' ELSE 'Visitante' END as "Estatus",
               c.tipo_conversacion as "Interacción", 
               c.registrado_por as "Staff"
        FROM conversaciones c 
        LEFT JOIN estudiantes e ON c.estudiante_id = e.id
        WHERE TO_CHAR(c.fecha, 'YYYY-MM') = '{mes_sel}'
        ORDER BY c.fecha DESC
    """
    df_historial = pd.read_sql_query(query_historial, engine)
    st.dataframe(df_historial, use_container_width=True, hide_index=True)

    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if not df_historial.empty:
            csv = df_historial.to_csv(index=False).encode('utf-8')
            st.download_button(label="⬇️ Descargar Todos los Datos (CSV)", data=csv, file_name=f"reporte_completo_{mes_sel}.csv", mime="text/csv", type="primary")

    st.markdown("### ⛪ Llevados a la Iglesia este mes")
    c.execute("SELECT semana_str, nombres_iglesia, registrado_por FROM reportes_grupales WHERE mes_pertenencia = %s AND nombres_iglesia != ''", (mes_sel,))
    iglesia_data = c.fetchall()
    if iglesia_data:
        for sem, nombres, reg_por in iglesia_data: 
            autor = reg_por if reg_por else "Alguien"
            st.info(f"**Semana {sem.split('W')[1]} (Reportado por {autor}):** {nombres}")
    else: st.write("No hay registros de iglesia este mes.")
    conn.close()

# =====================================================================
# 3. DIRECTORIO ESTUDIANTES
# =====================================================================
elif menu == "👤 Directorio Estudiantes":
    st.title("👤 Directorio de Estudiantes")
    tab1, tab2, tab3 = st.tabs(["📖 Consultar Directorio", "➕ Agregar Nuevo", "🔄 Cambiar Estado"])
    
    with tab1:
        filtro_estado = st.radio("Filtrar por estado:", ["Activos", "No participativos", "Graduados"], horizontal=True)
        estado_sql = "Activo" if filtro_estado == "Activos" else "No participativo" if filtro_estado == "No participativos" else "Graduado"
        df_consulta = pd.read_sql_query(f"SELECT nombre as \"Nombre\", categoria as \"Categoría\", telefono as \"Teléfono\", escuela as \"Escuela\", edad as \"Edad\", cumpleanos as \"Cumpleaños\" FROM estudiantes WHERE estado = '{estado_sql}' ORDER BY nombre", engine)
        st.dataframe(df_consulta, use_container_width=True, hide_index=True)

    with tab2:
        with st.form("form_nuevo_estudiante", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input("Nombre Completo *")
                categoria = st.selectbox("Camino de Fe *", ["Wanderer", "Sojourner", "Explorer", "Follower", "Guia"])
                edad = st.text_input("Edad")
            with c2:
                tel = st.text_input("Número de contacto")
                escuela = st.text_input("Escuela")
                cumple = st.text_input("Cumpleaños")
                
            if st.form_submit_button("Guardar Estudiante", type="primary"):
                if not nombre.strip(): st.error("El nombre es obligatorio.")
                else:
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("""INSERT INTO estudiantes (nombre, categoria, telefono, escuela, edad, cumpleanos) VALUES (%s, %s, %s, %s, %s, %s)""", 
                              (nombre.strip(), categoria, tel if tel else "Sin dato", escuela if escuela else "Sin dato", edad if edad else "Sin dato", cumple if cumple else "Sin dato"))
                    conn.commit(); conn.close()
                    st.success(f"Estudiante '{nombre}' guardado exitosamente.")

    with tab3:
        df_activos = pd.read_sql_query("SELECT id, nombre, estado FROM estudiantes WHERE estado IN ('Activo', 'No participativo') ORDER BY nombre", engine)
        if not df_activos.empty:
            for _, row in df_activos.iterrows():
                col_n, col_btn = st.columns([3, 1])
                col_n.write(f"**{row['nombre']}** - Actual: `{row['estado']}`")
                nuevo_estado = "No participativo" if row['estado'] == "Activo" else "Activo"
                texto_btn = "Pausar" if row['estado'] == "Activo" else "Reintegrar a Activos"
                if col_btn.button(texto_btn, key=f"btn_{row['id']}"):
                    conn = get_connection()
                    c = conn.cursor()
                    c.execute("UPDATE estudiantes SET estado = %s WHERE id = %s", (nuevo_estado, row['id']))
                    conn.commit(); conn.close(); st.rerun()

# =====================================================================
# 4. ADMINISTRACIÓN AVANZADA
# =====================================================================
elif menu == "⚙️ Administración Avanzada":
    st.title("⚙️ Base de Datos Maestra")
    pwd = st.text_input("Ingresa la contraseña de administrador:", type="password")
    
    if pwd == "elpozoregistradatos":
        tab_activos, tab_graduados, tab_importar, tab_borrar = st.tabs([
            "Estudiantes Activos/Inactivos", "🎓 Graduados", "📥 Importación", "🗑️ Eliminar Registros"
        ])
        
        with tab_activos:
            df_main = pd.read_sql_query("SELECT * FROM estudiantes WHERE estado != 'Graduado' ORDER BY id ASC", engine)
            edited_main = st.data_editor(df_main, key="editor_main", use_container_width=True, hide_index=True,
                                         column_config={"id": st.column_config.NumberColumn(disabled=True),
                                                        "estado": st.column_config.SelectboxColumn(options=["Activo", "No participativo", "Graduado"])})
            if st.button("💾 Guardar Cambios Generales"):
                conn = get_connection()
                c = conn.cursor()
                for _, row in edited_main.iterrows():
                    c.execute("""UPDATE estudiantes SET nombre=%s, categoria=%s, estado=%s, telefono=%s, escuela=%s, edad=%s, cumpleanos=%s WHERE id=%s""",
                              (row['nombre'], row['categoria'], row['estado'], row['telefono'], row['escuela'], row['edad'], row['cumpleanos'], row['id']))
                conn.commit(); conn.close(); st.success("Cambios guardados."); st.rerun()

        with tab_graduados:
            df_grad = pd.read_sql_query("SELECT * FROM estudiantes WHERE estado = 'Graduado' ORDER BY id ASC", engine)
            if not df_grad.empty:
                edited_grad = st.data_editor(df_grad, key="editor_grad", use_container_width=True, hide_index=True,
                                             column_config={"id": st.column_config.NumberColumn(disabled=True),
                                                            "estado": st.column_config.SelectboxColumn(options=["Graduado", "Activo"])})
                if st.button("💾 Guardar Cambios Graduados"):
                    conn = get_connection()
                    c = conn.cursor()
                    for _, row in edited_grad.iterrows():
                        c.execute("""UPDATE estudiantes SET nombre=%s, categoria=%s, estado=%s, telefono=%s, escuela=%s, edad=%s, cumpleanos=%s WHERE id=%s""",
                                  (row['nombre'], row['categoria'], row['estado'], row['telefono'], row['escuela'], row['edad'], row['cumpleanos'], row['id']))
                    conn.commit(); conn.close(); st.success("Cambios guardados."); st.rerun()

        with tab_importar:
            datos_pegados = st.text_area("Pega los datos de Excel aquí (Orden: Nombre | Categoría | Teléfono | Escuela | Edad | Cumpleaños):")
            if st.button("🚀 Importar Datos"):
                if datos_pegados.strip():
                    conn = get_connection()
                    c = conn.cursor()
                    conteo = 0
                    for linea in datos_pegados.strip().split('\n'):
                        if not linea.strip(): continue
                        cols = linea.split('\t')
                        while len(cols) < 6: cols.append("Sin dato")
                        if cols[0].strip():
                            c.execute("""INSERT INTO estudiantes (nombre, categoria, telefono, escuela, edad, cumpleanos) VALUES (%s, %s, %s, %s, %s, %s)""", 
                                      (cols[0].strip(), cols[1].strip() or "Wanderer", cols[2].strip() or "Sin dato", cols[3].strip() or "Sin dato", cols[4].strip() or "Sin dato", cols[5].strip() or "Sin dato"))
                            conteo += 1
                    conn.commit(); conn.close(); st.success(f"✅ Se agregaron {conteo} estudiantes.")
                
        with tab_borrar:
            df_est_del = pd.read_sql_query("SELECT id, nombre, estado FROM estudiantes", engine)
            dict_est_del = {f"{row['nombre']} ({row['estado']})": row['id'] for _, row in df_est_del.iterrows()}
            est_a_borrar = st.multiselect("Selecciona los estudiantes a eliminar:", list(dict_est_del.keys()))
            if est_a_borrar:
                with st.popover("⚠️ Borrar Estudiantes Seleccionados"):
                    st.warning("Estás a punto de borrar los estudiantes y su historial de forma irreversible.")
                    if st.button("Confirmar Eliminación Definitiva", type="primary"):
                        conn = get_connection()
                        c = conn.cursor()
                        for est in est_a_borrar:
                            id_del = dict_est_del[est]
                            c.execute("DELETE FROM conversaciones WHERE estudiante_id = %s", (id_del,))
                            c.execute("DELETE FROM estudiantes WHERE id = %s", (id_del,))
                        conn.commit(); conn.close(); st.success("Estudiantes eliminados."); st.rerun()

    elif pwd != "":
        st.error("Contraseña incorrecta.")
