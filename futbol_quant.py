import streamlit as st
import requests
import pandas as pd
import os
import math
from datetime import datetime, timedelta

# ==========================================
# 1. SEGURIDAD Y ACCESO QUANT
# ==========================================
st.set_page_config(page_title="Fútbol Quant V2.1", layout="wide", initial_sidebar_state="expanded")

def check_password():
    token = ""
    try:
        token = st.query_params.get("token", "")
    except:
        try:
            params = st.experimental_get_query_params()
            token = params.get("token", [""])[0]
        except: pass
        
    if token == "capo": st.session_state["password_correct"] = True
    if st.session_state.get("password_correct", False): return True

    st.markdown("""
    <style>
    .stApp { background-color: #05080F; color: #F8FAFC; }
    .login-box { background: #0F172A; border: 2px solid #38BDF8; border-radius: 20px; padding: 30px; margin-top: 5vh; box-shadow: 0 0 20px rgba(56, 189, 248, 0.2); }
    .login-title { color: #38BDF8; font-size: 26px; font-weight: 900; letter-spacing: 2px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<div class='login-title'>⚽ FÚTBOL QUANT V2.1</div>", unsafe_allow_html=True)
        st.markdown("<p style='color:#64748B; margin-bottom:20px; text-align: center;'>MOTOR GLOBAL LIBRE DE ERRORES</p>", unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Operador")
            p = st.text_input("Clave de Acceso", type="password")
            submit_btn = st.form_submit_button("AUTENTICAR SISTEMA", use_container_width=True)
            if submit_btn:
                if u == st.secrets.get("usuario", "") and p == st.secrets.get("password", ""):
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("❌ Acceso Denegado.")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

if not check_password(): st.stop()

# ==========================================
# 2. MOTOR EXTRACTOR HFT (ESPN API)
# ==========================================
LEAGUES = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "eng.1",
    "🇪🇸 La Liga": "esp.1",
    "🇩🇪 Bundesliga": "ger.1",
    "🇮🇹 Serie A": "ita.1",
    "🇺🇸 MLS": "usa.1",
    "🇧🇷 Brasileirão": "bra.1"
}

@st.cache_data(ttl=43200)
def extraer_datos_liga(league_slug):
    url_std = f"https://site.api.espn.com/apis/v2/sports/soccer/{league_slug}/standings"
    stats_equipos = {}
    
    try:
        res_std = requests.get(url_std).json()
        if 'children' in res_std: tabla = res_std['children'][0]['standings']['entries']
        else: tabla = res_std.get('standings', {}).get('entries', [])
        
        for fila in tabla:
            t_id = str(fila['team']['id'])
            stats = fila['stats']
            pj = next((s['value'] for s in stats if s['name'] == 'gamesPlayed'), 0)
            gf = next((s['value'] for s in stats if s['name'] == 'pointsFor'), 0)
            gc = next((s['value'] for s in stats if s['name'] == 'pointsAgainst'), 0)
            if pj > 0:
                stats_equipos[t_id] = {"ataque": round(gf / pj, 2), "defensa": round(gc / pj, 2)}
    except: pass

    url_score = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard"
    partidos_list = []
    try:
        res_score = requests.get(url_score).json()
        for evento in res_score.get('events', []):
            if evento['status']['type']['state'] == 'pre':
                comp = evento['competitions'][0]
                t1_info = comp['competitors'][0]
                t2_info = comp['competitors'][1]
                s1 = stats_equipos.get(str(t1_info['team']['id']), {"ataque": 1.2, "defensa": 1.2})
                s2 = stats_equipos.get(str(t2_info['team']['id']), {"ataque": 1.2, "defensa": 1.2})
                partidos_list.append({
                    "id": evento['id'],
                    "t1": t1_info['team']['displayName'],
                    "t2": t2_info['team']['displayName'],
                    "img1": t1_info['team'].get('logo', 'https://via.placeholder.com/50'),
                    "img2": t2_info['team'].get('logo', 'https://via.placeholder.com/50'),
                    "begin_at": evento['date'],
                    "xg_local": s1['ataque'] * s2['defensa'],
                    "xg_visitante": s2['ataque'] * s1['defensa'],
                    "corners_base": (s1['ataque'] + s2['ataque']) * 3.6,
                    "shots_base": (s1['ataque'] + s2['ataque']) * 5.2
                })
    except: pass
    return partidos_list

# ==========================================
# 3. MOTOR CUANTITATIVO FÚTBOL
# ==========================================
def motor_futbol(xg_l, xg_v, c_base, s_base, mercado, opcion, linea, clima, lesion, localia):
    if localia == "Fuerte (Fortín)": xg_l *= 1.15; xg_v *= 0.90
    if lesion == "Estrella Local": xg_l *= 0.80; s_base *= 0.85
    elif lesion == "Estrella Visitante": xg_v *= 0.80
    if clima == "Lluvia/Barro": xg_l *= 0.92; xg_v *= 0.92; c_base *= 1.22 

    prob = 0.50
    if "Ganador" in mercado:
        total_xg = (xg_l + xg_v) if (xg_l + xg_v) > 0 else 1
        if opcion == "Local": prob = xg_l / total_xg + 0.08 
        elif opcion == "Visitante": prob = xg_v / total_xg
        else: prob = 1 - ((xg_l / total_xg + 0.08) + (xg_v / total_xg)) 
    elif "Total de Goles" in mercado:
        prob = 0.5 + ((xg_l + xg_v) - linea) * 0.15
        if "Menos" in opcion: prob = 1 - prob
    elif "Handicap" in mercado:
        prob = 0.5 + ((xg_l - xg_v) + linea) * 0.20
        if opcion == "Visitante": prob = 1 - prob
    elif "Córners" in mercado:
        if "1er Tiempo" in mercado: c_base *= 0.46 
        prob = 0.5 + (c_base - linea) * 0.12
        if "Menos" in opcion: prob = 1 - prob
    elif "Tiros" in mercado:
        prob = 0.5 + (s_base - linea) * 0.10
        if "Menos" in opcion: prob = 1 - prob

    return max(0.05, min(0.95, prob))

# ==========================================
# 4. CSS Y ESTILOS (IGUAL A ESPORTS)
# ==========================================
st.sidebar.markdown("### 🎨 Apariencia")
tema = st.sidebar.selectbox("", ["Azul Oscuro (Defecto)", "Verde Hacker", "Rojo Táctico"])
colors = {"Azul Oscuro (Defecto)": ("#0B1120", "#1E293B", "#F1F5F9", "#38BDF8"), "Verde Hacker": ("#000000", "#051A05", "#4ADE80", "#10B981"), "Rojo Táctico": ("#0A0000", "#1A0505", "#FECACA", "#EF4444")}
c_bg, c_card, c_text, c_acc = colors[tema]
c_sub, c_border, c_btn = "#94A3B8", "#334155", "#0F172A"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {c_bg}; color: {c_text}; font-family: 'Inter', sans-serif; }}
    [data-testid="stSidebar"] {{ background-color: {c_card} !important; border-right: 1px solid {c_border}; }}
    .glass-card {{ background: {c_card}; border: 1px solid {c_border}; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 4px solid {c_acc}; }}
    .team-logo {{ width: 50px; height: 50px; background: white; border-radius: 50%; padding: 3px; }}
    .badge-time {{ background: {c_acc}; color: {c_bg}; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; }}
    .prob-box {{ background: {c_btn}; padding: 15px; border-radius: 8px; border: 1px solid {c_acc}; text-align: center; }}
    .prob-number {{ font-size: 32px; font-weight: 900; color: {c_acc}; }}
    .stream-btn {{ background-color: #0046E4; color: white !important; padding: 8px; border-radius: 8px; text-decoration: none; font-size: 11px; display: block; text-align: center; margin-top: 10px; font-weight: bold; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. SIDEBAR Y LIGAS
# ==========================================
st.sidebar.markdown("---")
liga_sel = st.sidebar.radio("🏆 Competición", list(LEAGUES.keys()))
if st.sidebar.button("🔄 Sincronizar ESPN", use_container_width=True): st.cache_data.clear(); st.rerun()

# ==========================================
# 6. RADAR PRINCIPAL (PARCHE DE FECHA APLICADO)
# ==========================================
st.markdown(f"<h2 style='color:{c_text};'>⚽ Radar Quant: {liga_sel[3:]}</h2>", unsafe_allow_html=True)

hoy_bol = datetime.utcnow() - timedelta(hours=4)
partidos_raw = extraer_datos_liga(LEAGUES[liga_sel])

if not partidos_raw:
    st.info("No hay partidos programados próximamente.")
else:
    c1, c2 = st.columns(2)
    for i, p in enumerate(partidos_raw[:16]):
        # --- PARCHE DE FECHA ---
        try:
            # Limpiamos la fecha de ESPN para que siempre sea compatible
            fecha_limpia = p['begin_at'].replace('Z', '').split('.')[0]
            dt_partido_bol = datetime.strptime(fecha_limpia, "%Y-%m-%dT%H:%M") - timedelta(hours=4)
        except:
            continue # Si la fecha viene rota, saltamos el partido para no colapsar
        
        if dt_partido_bol < hoy_bol - timedelta(hours=3): continue

        with (c1 if i % 2 == 0 else c2):
            st.markdown(f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between; margin-bottom:10px;">
                    <span style="font-size:10px; color:{c_sub}; uppercase;">{liga_sel[3:]}</span>
                    <span class="badge-time">{dt_partido_bol.strftime('%d/%m %H:%M')}</span>
                </div>
                <div style="display: flex; justify-content: space-around; align-items: center; text-align: center;">
                    <div style="width: 40%; font-size:13px;"><b>{p['t1']}</b><br><img src="{p['img1']}" class="team-logo"></div>
                    <div style="color:{c_acc}; font-weight:bold;">VS</div>
                    <div style="width: 40%; font-size:13px;"><b>{p['t2']}</b><br><img src="{p['img2']}" class="team-logo"></div>
                </div>
                <a href="https://www.disneyplus.com/" target="_blank" class="stream-btn">▶️ VER EN DISNEY+ / STAR+</a>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("⚙️ Operar Pronóstico"):
                col_a, col_b, col_c = st.columns(3)
                clima = col_a.selectbox("Clima", ["Normal", "Lluvia/Barro"], key=f"cl_{i}")
                lesion = col_b.selectbox("Bajas", ["Ninguna", "Estrella Local", "Estrella Visitante"], key=f"ls_{i}")
                localia = col_c.selectbox("Localía", ["Normal", "Fuerte (Fortín)"], key=f"lc_{i}")
                
                mercados = ["-- Seleccione --", "Ganador del Partido", "Total de Goles", "Handicap Goles", "Córners Totales", "Córners 1er Tiempo", "Tiros a Puerta"]
                sel_mer = st.selectbox("Mercado:", mercados, key=f"me_{i}")
                
                if sel_mer != "-- Seleccione --":
                    col_izq, col_der = st.columns(2)
                    with col_izq:
                        if "Ganador" in sel_mer: op = st.radio("Opción:", ["Local", "Empate", "Visitante"], key=f"o_{i}")
                        elif "Handicap" in sel_mer: op = st.radio("Opción:", ["Local", "Visitante"], key=f"o_{i}")
                        else: op = st.radio("Opción:", ["Más (+)", "Menos (-)"], key=f"o_{i}")
                        lin = st.number_input("Línea:", value=2.5 if "Goles" in sel_mer else 9.5, step=0.5, key=f"li_{i}")
                    
                    with col_der:
                        prob = motor_futbol(p['xg_local'], p['xg_visitante'], p['corners_base'], p['shots_base'], sel_mer, op, lin, clima, lesion, localia)
                        st.markdown(f"""<div class="prob-box"><div style="font-size:10px;">PROBABILIDAD</div><div class="prob-number">{prob*100:.1f}%</div><div style="font-size:10px;">Cuota Mín: {1/prob:.2f}</div></div>""", unsafe_allow_html=True)