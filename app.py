import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ministerio App", page_icon="🌱", layout="wide")

# --- INICIALIZACIÓN Y ACTUALIZACIÓN DE BASE DE DATOS ---
def inicializar_bd():
    conn = sqlite3.connect('ministerio.db')
    cursor = conn.cursor()
    
    # Tablas base
    cursor.execute('''CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, categoria TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS conversaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT, estudiante_id INTEGER, tipo_conversacion TEXT, fecha DATE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS actividades_semanales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, semana_str TEXT, mes_pertenencia TEXT, 
        grupos_realizados INTEGER, grupos_iniciados INTEGER, nombres_iglesia TEXT)''')
    
    # Asegurar que existan las columnas extra
    columnas_estudiantes = {
        "estado": "TEXT DEFAULT 'Activo'", "telefono": "TEXT DEFAULT 'Sin dato'", 
        "escuela": "TEXT DEFAULT 'Sin dato'", "edad": "TEXT DEFAULT 'Sin dato'", "cumpleanos": "TEXT DEFAULT 'Sin dato'"
    }
    for col, tipo in columnas_estudiantes.items():
        try: cursor.execute(f"ALTER TABLE estudiantes ADD COLUMN {col} {tipo}")
        except: pass

    columnas_conversaciones = {"registrado_por": "TEXT", "nombre_visitante": "TEXT"}
    for col, tipo in columnas_conversaciones.items():
        try: cursor.execute(f"ALTER TABLE conversaciones ADD COLUMN {col} {tipo}")
        except: pass

    conn.commit()
    conn.close()

inicializar_bd()

# --- FUNCIONES AUXILIARES ---
def obtener_semana_actual():
    hoy = date.today()
    num_semana = hoy.isocalendar()[1]
    return f"{hoy.year}-W{num_semana:02d}", hoy.strftime("%Y-%m")

if 'alerta_registro' not in st.session_state:
    st.session_state['alerta_registro'] = None

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
    "📝 Registrar Interacción", 
    "📊 Resumen Mensual",
    "👤 Directorio Estudiantes", 
    "👥 Reporte Semanal",
    "⚙️ Administración Avanzada"
])

# =====================================================================
# 1. REGISTRAR INTERACCIÓN
# =====================================================================
if menu == "📝 Registrar Interacción":
    st.title("📝 Registrar Interacciones")
    
    # --- ALERTA REGLA DE 3 VECES (Aparece fuera del formulario para no borrarse) ---
    if st.session_state['alerta_registro']:
        visitante = st.session_state['alerta_registro']
        st.warning(f"🔔 **¡Atención!** El visitante **{visitante}** ha acumulado un múltiplo de 3 interacciones. ¿Deseas agregarlo oficialmente como estudiante?")
        
        col_y, col_n = st.columns([1, 4])
        with col_y:
            with st.popover("Sí, registrar ahora"):
                st.write(f"Registrando a: {visitante}")
                cat = st.selectbox("Categoría*", ["Wanderer", "Sojourner", "Explorer", "Follower", "Guia"])
                if st.button("Guardar Oficialmente"):
                    conn = sqlite3.connect('ministerio.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO estudiantes (nombre, categoria) VALUES (?, ?)", (visitante, cat))
                    nuevo_id = c.lastrowid
                    c.execute("UPDATE conversaciones SET estudiante_id = ?, nombre_visitante = NULL WHERE nombre_visitante = ?", (nuevo_id, visitante))
                    conn.commit()
                    conn.close()
                    st.session_state['alerta_registro'] = None
                    st.success("¡Registrado y vinculado con éxito!")
                    st.rerun()
        with col_n:
            if st.button("No por ahora"):
                st.session_state['alerta_registro'] = None
                st.rerun()
        st.markdown("---")

    conn = sqlite3.connect('ministerio.db')
    estudiantes_activos = pd.read_sql_query("SELECT id, nombre, categoria FROM estudiantes WHERE estado = 'Activo' ORDER BY nombre", conn)
    visitantes_previos = pd.read_sql_query("SELECT DISTINCT nombre_visitante FROM conversaciones WHERE nombre_visitante IS NOT NULL", conn)
    conn.close()

    nombres_dict = {f"{row['nombre']} ({row['categoria']})": row['id'] for _, row in estudiantes_activos.iterrows()}
    lista_visitantes = visitantes_previos['nombre_visitante'].tolist() if not visitantes_previos.empty else []

    # FORMULARIO CON AUTO-LIMPIEZA (clear_on_submit=True)
    with st.form("form_registro", clear_on_submit=True):
        st.markdown("Al guardar, las casillas se limpiarán solas para que puedas registrar el siguiente rápidamente.")
        col1, col2 = st.columns(2)
        with col1:
            usuario = st.text_input("👤 Tu Nombre (Quien registra)*")
            fecha_conv = st.date_input("📅 Fecha", date.today())
            tipo_conv = st.selectbox("💬 Tipo", ["1a1", "Conversaciones con Jesus", "Conversaciones intencionales"])
        
        with col2:
            st.markdown("**1. Estudiantes Oficiales**")
            est_seleccionados = st.multiselect("Selecciona uno o varios:", list(nombres_dict.keys()))
            
            st.markdown("**2. Visitantes / No Registrados**")
            visitante_existente = st.selectbox("Sugerencias de meses pasados (Opcional):", [""] + lista_visitantes)
            visitante_nuevo = st.text_input("O escribe un nombre nuevo (Opcional):")

        submit = st.form_submit_button("Guardar Registros", use_container_width=True, type="primary")
        
        if submit:
            visitante_final = visitante_nuevo.strip() if visitante_nuevo.strip() else visitante_existente
            
            if not usuario.strip():
                st.error("Debes ingresar tu nombre.")
            elif not est_seleccionados and not visitante_final:
                st.error("Debes seleccionar al menos un estudiante o ingresar un visitante.")
            else:
                conn = sqlite3.connect('ministerio.db')
                c = conn.cursor()
                fecha_str = fecha_conv.strftime("%Y-%m-%d")
                
                for est in est_seleccionados:
                    c.execute("INSERT INTO conversaciones (estudiante_id, tipo_conversacion, fecha, registrado_por) VALUES (?, ?, ?, ?)", 
                              (nombres_dict[est], tipo_conv, fecha_str, usuario.strip()))
                
                if visitante_final:
                    c.execute("INSERT INTO conversaciones (nombre_visitante, tipo_conversacion, fecha, registrado_por) VALUES (?, ?, ?, ?)", 
                              (visitante_final, tipo_conv, fecha_str, usuario.strip()))
                    
                    c.execute("SELECT COUNT(*) FROM conversaciones WHERE nombre_visitante = ?", (visitante_final,))
                    conteo = c.fetchone()[0]
                    if conteo > 0 and conteo % 3 == 0:
                        st.session_state['alerta_registro'] = visitante_final

                conn.commit()
                conn.close()
                st.success('¡Registrado con éxito! Las casillas han sido limpiadas.')
                if st.session_state['alerta_registro']:
                    st.rerun()

# =====================================================================
# 2. RESUMEN MENSUAL
# =====================================================================
elif menu == "📊 Resumen Mensual":
    st.title("📊 Resumen Mes a Mes")
    
    conn = sqlite3.connect('ministerio.db')
    meses_df = pd.read_sql_query("SELECT DISTINCT strftime('%Y-%m', fecha) as mes FROM conversaciones UNION SELECT mes_pertenencia FROM actividades_semanales", conn)
    historial = [m for m in meses_df['mes'].dropna().tolist()]
    if not historial: historial = [date.today().strftime("%Y-%m")]
    historial.sort(reverse=True)
    
    mes_sel = st.selectbox("📅 Selecciona el mes a analizar:", historial)
    st.divider()

    c = conn.cursor()
    c.execute('''SELECT COUNT(DISTINCT estudiante_id) FROM conversaciones 
                 WHERE tipo_conversacion = 'Conversaciones con Jesus' AND strftime('%Y-%m', fecha) = ? AND estudiante_id IS NOT NULL''', (mes_sel,))
    unicas_jesus = c.fetchone()[0]

    c.execute('''SELECT SUM(grupos_realizados), SUM(grupos_iniciados) FROM actividades_semanales WHERE mes_pertenencia = ?''', (mes_sel,))
    sumas_grupales = c.fetchone()
    total_g_realizados = sumas_grupales[0] if sumas_grupales[0] else 0
    total_g_iniciados = sumas_grupales[1] if sumas_grupales[1] else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("🌟 Con Jesús (Personas Únicas)", unicas_jesus)
    col2.metric("👥 Grupos Realizados (Total Mes)", total_g_realizados)
    col3.metric("🚀 Grupos Iniciados (Total Mes)", total_g_iniciados)

    st.markdown("### 📈 Conteo por Estudiante (Rendimiento)")
    query_est = f"""
        SELECT e.nombre as 'Estudiante', e.estado as 'Estado',
        SUM(CASE WHEN c.tipo_conversacion = '1a1' THEN 1 ELSE 0 END) as '1a1',
        SUM(CASE WHEN c.tipo_conversacion = 'Conversaciones con Jesus' THEN 1 ELSE 0 END) as 'Con Jesús',
        SUM(CASE WHEN c.tipo_conversacion = 'Conversaciones intencionales' THEN 1 ELSE 0 END) as 'Intencionales',
        COUNT(c.id) as 'Total General'
        FROM conversaciones c
        JOIN estudiantes e ON c.estudiante_id = e.id
        WHERE strftime('%Y-%m', c.fecha) = '{mes_sel}'
        GROUP BY e.id ORDER BY 'Total General' DESC
    """
    df_rendimiento = pd.read_sql_query(query_est, conn)
    st.dataframe(df_rendimiento, use_container_width=True, hide_index=True)

    st.markdown("### ⛪ Llevados a la Iglesia este mes")
    c.execute("SELECT semana_str, nombres_iglesia FROM actividades_semanales WHERE mes_pertenencia = ? AND nombres_iglesia != ''", (mes_sel,))
    iglesia_data = c.fetchall()
    if iglesia_data:
        for sem, nombres in iglesia_data:
            st.info(f"**Semana {sem.split('W')[1]}:** {nombres}")
    else:
        st.write("No hay registros este mes.")
    conn.close()

# =====================================================================
# 3. DIRECTORIO ESTUDIANTES (MODIFICADO: SOLO LECTURA + AUTO-LIMPIEZA)
# =====================================================================
elif menu == "👤 Directorio Estudiantes":
    st.title("👤 Directorio de Estudiantes")
    
    tab1, tab2, tab3 = st.tabs(["📖 Consultar Directorio", "➕ Agregar Nuevo", "🔄 Cambiar Estado"])
    
    # Taba 1: SOLO LECTURA
    with tab1:
        st.write("Explora la base de datos de manera segura (No se puede editar desde aquí).")
        filtro_estado = st.radio("Filtrar por estado:", ["Activos", "No participativos", "Graduados"], horizontal=True)
        
        estado_sql = "Activo"
        if filtro_estado == "No participativos": estado_sql = "No participativo"
        elif filtro_estado == "Graduados": estado_sql = "Graduado"
        
        conn = sqlite3.connect('ministerio.db')
        df_consulta = pd.read_sql_query(f"SELECT nombre as 'Nombre', categoria as 'Categoría', telefono as 'Teléfono', escuela as 'Escuela', edad as 'Edad', cumpleanos as 'Cumpleaños' FROM estudiantes WHERE estado = '{estado_sql}' ORDER BY nombre", conn)
        conn.close()
        
        st.dataframe(df_consulta, use_container_width=True, hide_index=True)

    # Taba 2: AGREGAR NUEVO CON AUTO-LIMPIEZA
    with tab2:
        with st.form("form_nuevo_estudiante", clear_on_submit=True):
            st.markdown("Los campos con * son obligatorios. Al guardar, se limpiarán los datos automáticamente.")
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input("Nombre Completo *")
                categoria = st.selectbox("Camino de Fe *", ["Wanderer", "Sojourner", "Explorer", "Follower", "Guia"])
                edad = st.text_input("Edad")
            with c2:
                tel = st.text_input("Número de contacto")
                escuela = st.text_input("Escuela")
                cumple = st.text_input("Cumpleaños (Ej. 15 de Mayo)")
                
            if st.form_submit_button("Guardar Estudiante", type="primary"):
                if not nombre.strip():
                    st.error("El nombre es obligatorio.")
                else:
                    conn = sqlite3.connect('ministerio.db')
                    conn.execute("""INSERT INTO estudiantes (nombre, categoria, telefono, escuela, edad, cumpleanos) 
                                 VALUES (?, ?, ?, ?, ?, ?)""", 
                              (nombre.strip(), categoria, tel if tel else "Sin dato", escuela if escuela else "Sin dato", edad if edad else "Sin dato", cumple if cumple else "Sin dato"))
                    conn.commit()
                    conn.close()
                    st.success(f"Estudiante '{nombre}' guardado exitosamente.")

    # Taba 3: CAMBIAR ESTADO
    with tab3:
        st.write("Mueve a los estudiantes inactivos a 'No participativos' para que no saturen la lista al registrar conversaciones.")
        conn = sqlite3.connect('ministerio.db')
        df_activos = pd.read_sql_query("SELECT id, nombre, estado FROM estudiantes WHERE estado IN ('Activo', 'No participativo') ORDER BY nombre", conn)
        
        if not df_activos.empty:
            for _, row in df_activos.iterrows():
                col_n, col_btn = st.columns([3, 1])
                col_n.write(f"**{row['nombre']}** - Actual: `{row['estado']}`")
                
                nuevo_estado = "No participativo" if row['estado'] == "Activo" else "Activo"
                texto_btn = "Pausar" if row['estado'] == "Activo" else "Reintegrar a Activos"
                
                if col_btn.button(texto_btn, key=f"btn_{row['id']}"):
                    conn.execute("UPDATE estudiantes SET estado = ? WHERE id = ?", (nuevo_estado, row['id']))
                    conn.commit()
                    st.rerun()
        conn.close()

# =====================================================================
# 4. REPORTE SEMANAL
# =====================================================================
elif menu == "👥 Reporte Semanal":
    st.title("📅 Reporte de Grupos e Iglesia")
    
    semana_actual, mes_actual = obtener_semana_actual()
    st.write(f"Estás reportando para la **Semana {semana_actual.split('W')[1]}** (Pertenece a {mes_actual}).")
    
    conn = sqlite3.connect('ministerio.db')
    c = conn.cursor()
    c.execute("SELECT grupos_realizados, nombres_iglesia, grupos_iniciados FROM actividades_semanales WHERE semana_str = ?", (semana_actual,))
    datos_sem = c.fetchone()
    
    with st.form("form_semanal", clear_on_submit=False):
        r = st.number_input("¿Cuántos grupitos basados en la fe tuviste en esta semana?", min_value=0, value=datos_sem[0] if datos_sem else 0)
        i = st.number_input("¿Cuántos grupitos basados en la fe se arrancaron la semana pasada?", min_value=0, value=datos_sem[2] if datos_sem else 0)
        n = st.text_area("¿A quién llevaste a la iglesia esta semana? (Escribe los nombres separados por comas)", value=datos_sem[1] if datos_sem else "")
        
        if st.form_submit_button("Guardar Reporte Semanal", type="primary"):
            if datos_sem:
                c.execute("UPDATE actividades_semanales SET grupos_realizados=?, grupos_iniciados=?, nombres_iglesia=? WHERE semana_str=?", 
                          (r, i, n, semana_actual))
            else:
                c.execute("INSERT INTO actividades_semanales (semana_str, mes_pertenencia, grupos_realizados, grupos_iniciados, nombres_iglesia) VALUES (?, ?, ?, ?, ?)", 
                          (semana_actual, mes_actual, r, i, n))
            conn.commit()
            st.success("Guardado correctamente.")
    conn.close()

# =====================================================================
# 5. ADMINISTRACIÓN AVANZADA
# =====================================================================
elif menu == "⚙️ Administración Avanzada":
    st.title("⚙️ Base de Datos Maestra")
    
    pwd = st.text_input("Ingresa la contraseña de administrador:", type="password")
    
    if pwd == "elpozoregistradatos":
        st.success("Acceso concedido.")
        conn = sqlite3.connect('ministerio.db')
        
        tab_activos, tab_graduados, tab_importar = st.tabs(["Estudiantes Activos/Inactivos", "🎓 Hoja de Graduados", "📥 Importación Masiva (Copiar y Pegar)"])
        
        with tab_activos:
            st.write("Haz doble clic en cualquier celda para editar. Al terminar presiona Guardar.")
            df_main = pd.read_sql_query("SELECT * FROM estudiantes WHERE estado != 'Graduado'", conn)
            edited_main = st.data_editor(df_main, key="editor_main", use_container_width=True, hide_index=True,
                                         column_config={"id": st.column_config.NumberColumn(disabled=True),
                                                        "estado": st.column_config.SelectboxColumn(options=["Activo", "No participativo", "Graduado"])})
            if st.button("💾 Guardar Cambios Generales"):
                c = conn.cursor()
                for _, row in edited_main.iterrows():
                    c.execute("""UPDATE estudiantes SET nombre=?, categoria=?, estado=?, telefono=?, escuela=?, edad=?, cumpleanos=? WHERE id=?""",
                              (row['nombre'], row['categoria'], row['estado'], row['telefono'], row['escuela'], row['edad'], row['cumpleanos'], row['id']))
                conn.commit()
                st.success("Cambios guardados.")
                st.rerun()

        with tab_graduados:
            df_grad = pd.read_sql_query("SELECT * FROM estudiantes WHERE estado = 'Graduado'", conn)
            if df_grad.empty:
                st.info("Aún no tienes estudiantes graduados.")
            else:
                edited_grad = st.data_editor(df_grad, key="editor_grad", use_container_width=True, hide_index=True,
                                             column_config={"id": st.column_config.NumberColumn(disabled=True),
                                                            "estado": st.column_config.SelectboxColumn(options=["Graduado", "Activo"])})
                if st.button("💾 Guardar Cambios de Graduados"):
                    c = conn.cursor()
                    for _, row in edited_grad.iterrows():
                        c.execute("""UPDATE estudiantes SET nombre=?, categoria=?, estado=?, telefono=?, escuela=?, edad=?, cumpleanos=? WHERE id=?""",
                                  (row['nombre'], row['categoria'], row['estado'], row['telefono'], row['escuela'], row['edad'], row['cumpleanos'], row['id']))
                    conn.commit()
                    st.success("Cambios guardados.")
                    st.rerun()

        # NUEVA PESTAÑA: IMPORTACIÓN MASIVA
        with tab_importar:
            st.markdown("### 📥 Agrega múltiples estudiantes desde Excel o Google Sheets")
            st.info("**Instrucciones:** Selecciona las filas en tu Excel, dale a 'Copiar' y luego 'Pegar' dentro del cuadro de texto de abajo.")
            
            st.markdown("**🚨 EL ORDEN EXACTO DE TUS COLUMNAS EN EXCEL DEBE SER ESTE:**")
            st.code("Nombre | Categoría | Teléfono | Escuela | Edad | Cumpleaños")
            st.markdown("*(Si alguien no tiene teléfono o escuela, deja la celda en blanco en tu Excel pero no borres la columna)*")
            
            datos_pegados = st.text_area("Pega los datos de Excel aquí:", height=200, placeholder="Juan Perez\tWanderer\t555-1234\tUVM\t20\t12 de Marzo\nAna Gomez\tExplorer\t...\t...\t...\t...")
            
            if st.button("🚀 Importar Datos Ahora", type="primary"):
                if datos_pegados.strip():
                    c = conn.cursor()
                    lineas = datos_pegados.strip().split('\n')
                    conteo_exito = 0
                    
                    for linea in lineas:
                        if not linea.strip(): continue
                        # Al pegar desde Excel, las columnas se separan por una tabulación (\t)
                        cols = linea.split('\t')
                        
                        # Rellenar con "Sin dato" si el Excel tiene menos de 6 columnas
                        while len(cols) < 6: cols.append("Sin dato")
                        
                        nom = cols[0].strip()
                        cat = cols[1].strip() if cols[1].strip() else "Wanderer"
                        tel = cols[2].strip() if cols[2].strip() else "Sin dato"
                        esc = cols[3].strip() if cols[3].strip() else "Sin dato"
                        eda = cols[4].strip() if cols[4].strip() else "Sin dato"
                        cum = cols[5].strip() if cols[5].strip() else "Sin dato"
                        
                        if nom:
                            c.execute("""INSERT INTO estudiantes (nombre, categoria, telefono, escuela, edad, cumpleanos) 
                                         VALUES (?, ?, ?, ?, ?, ?)""", (nom, cat, tel, esc, eda, cum))
                            conteo_exito += 1
                    
                    conn.commit()
                    st.success(f"✅ ¡Importación exitosa! Se agregaron {conteo_exito} estudiantes a la base de datos.")
                else:
                    st.error("No hay datos para importar. Por favor pega la información de Excel en el cuadro.")
                    
        conn.close()
    elif pwd != "":
        st.error("Contraseña incorrecta.")
