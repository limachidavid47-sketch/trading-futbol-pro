import streamlit as st
import requests
import os
import math
from datetime import datetime, timedelta

# ==========================================
# 1. SEGURIDAD, ACCESO QUANT Y ENLACE MÁGICO
# ==========================================
st.set_page_config(page_title="Quant Elite V33.1", layout="wide", initial_sidebar_state="expanded")

def check_password():
    token = ""
    try:
        token = st.query_params.get("token", "")
    except:
        try:
            params = st.experimental_get_query_params()
            token = params.get("token", [""])[0]
        except: pass
        
    if token == "capo": 
        st.session_state["password_correct"] = True
        
    if st.session_state.get("password_correct", False): 
        return True

    st.markdown("""
    <style>
    .stApp { background-color: #05080F; color: #F8FAFC; }
    .login-box { background: #0F172A; border: 2px solid #10B981; border-radius: 20px; padding: 30px; margin-top: 5vh; box-shadow: 0 0 20px rgba(16, 185, 129, 0.2); }
    .login-title { color: #10B981; font-size: 26px; font-weight: 900; letter-spacing: 2px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<div class='login-title'>⚡ QUANT TERMINAL V33.1</div>", unsafe_allow_html=True)
        st.markdown("<p style='color:#64748B; margin-bottom:20px; text-align: center;'>OMNI-SISTEMA HFT (MOBAs + FPS)</p>", unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Operador")
            p = st.text_input("Clave de Acceso", type="password")
            submit_btn = st.form_submit_button("AUTENTICAR SISTEMA", use_container_width=True)
            
            if submit_btn:
                if u == st.secrets.get("usuario", "") and p == st.secrets.get("password", ""):
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: 
                    st.error("❌ Acceso Denegado.")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

if not check_password(): st.stop()

# ==========================================
# 2. MOTOR DE DATOS HFT
# ==========================================
API_KEY = "F163TaN2efiwM8Ejb3xj0FWaeFAWzQgjbW8bPcuQwi9-ct_ZD4g"

@st.cache_data(ttl=60)
def call_api_live(game_slug, endpoint, params_str=""):
    url = f"https://api.pandascore.co/{game_slug}/{endpoint}?{params_str}"
    headers = {"accept": "application/json", "authorization": f"Bearer {API_KEY}"}
    try:
        res = requests.get(url, headers=headers)
        return res.json() if res.status_code == 200 else []
    except: return []

@st.cache_data(ttl=21600, show_spinner=False)
def fetch_historical_data(game_slug, team_id):
    url = f"https://api.pandascore.co/{game_slug}/matches"
    params = f"filter[opponent_id]={team_id}&filter[status]=finished&sort=-end_at&per_page=10"
    headers = {"accept": "application/json", "authorization": f"Bearer {API_KEY}"}
    try:
        res = requests.get(f"{url}?{params}", headers=headers)
        if res.status_code == 200:
            hist = res.json()
            if not hist: return [], 0.50, ['unknown']*5
            wins = sum(1 for m in hist if str(m.get('winner_id')) == str(team_id))
            form = ['win' if str(m.get('winner_id')) == str(team_id) else 'loss' for m in hist]
            return hist, (wins/len(hist)), (form[:5])
    except: pass
    return [], 0.50, ['unknown']*5

def gestionar_bank(monto=None):
    if not os.path.exists("bank.txt"):
        with open("bank.txt", "w") as f: f.write("100.0")
    if monto is not None:
        with open("bank.txt", "w") as f: f.write(str(round(monto, 2)))
    with open("bank.txt", "r") as f: return float(f.read())

bank_actual = gestionar_bank()

# ==========================================
# 3. MOTORES CUANTITATIVOS 
# ==========================================
def calculate_gold_impact(gold_diff, minute, game_slug):
    if minute <= 0: return 0
    if game_slug == "dota2": divisor, pivote = 10000, 30
    # PARCHE: Cambiado a "mlbb" para que detecte bien el impacto del oro
    elif game_slug == "mlbb": divisor, pivote = 5000, 12 
    else: divisor, pivote = 8000, 25
    impacto_bruto = gold_diff / divisor
    return max(-0.40, min(0.40, impacto_bruto * (1 / (1 + (minute / pivote)**2))))

def motor_moba(wr1, wr2, mercado, opcion, linea_casino, t1_name):
    prob_base = 0.50
    total_wr = wr1 + wr2 if (wr1 + wr2) > 0 else 1
    es_eq1 = (opcion == t1_name)

    if "Ganador" in mercado or ("Kills por" in mercado and "Carrera" not in mercado):
        prob_base = wr1 / total_wr if es_eq1 else wr2 / total_wr
    elif "Handicap" in mercado:
        prob_win = wr1 / total_wr if es_eq1 else wr2 / total_wr
        dificultad = (abs(linea_casino) * 0.025)
        prob_base = prob_win - dificultad if linea_casino < 0 else prob_win + dificultad
    elif "Total" in mercado or "Duración" in mercado:
        mom = (wr1 + wr2) / 2
        prob_base = 0.50 + (mom - 0.50) * 0.3 if "Más" in opcion else 0.50 - (mom - 0.50) * 0.3
        if linea_casino > 35: prob_base += 0.10 if "Más" not in opcion else 0
    elif "Primer" in mercado or "Primera" in mercado:
        prob_base = 0.50 + (((wr1 / total_wr if es_eq1 else wr2 / total_wr) - 0.50) * 0.7)
    elif "Carrera" in mercado:
        var = 0.60 if "5" in mercado else 0.75 if "10" in mercado else 0.85
        prob_base = 0.50 + (((wr1 / total_wr if es_eq1 else wr2 / total_wr) - 0.50) * var)
    return max(0.05, min(0.95, prob_base))

def motor_fps(wr1, wr2, mercado, opcion, linea, t1_name, f_blood, eco_adv):
    total_wr = wr1 + wr2 if (wr1 + wr2) > 0 else 1
    es_eq1 = (opcion == t1_name)
    prob_base = wr1 / total_wr if es_eq1 else wr2 / total_wr

    if "Handicap" in mercado:
        if "Mapas" in mercado: dificultad = (abs(linea) * 0.15)
        else: dificultad = (abs(linea) * 0.04)
        prob_base = prob_base - dificultad if linea < 0 else prob_base + dificultad
        
    elif "Total" in mercado:
        mom = (wr1 + wr2) / 2
        prob_base = 0.5 + (mom - 0.5) * 0.4 if "Más" in opcion else 0.5 - (mom - 0.5) * 0.4
        
    elif "Carrera" in mercado:
        var = 0.55 if "5" in mercado else 0.70 if "9" in mercado else 0.85
        prob_base = 0.50 + (((wr1 / total_wr if es_eq1 else wr2 / total_wr) - 0.50) * var)
        
    elif "Pistolas" in mercado:
        prob_base = 0.50 + (((wr1 / total_wr if es_eq1 else wr2 / total_wr) - 0.50) * 0.4) 

    if f_blood == "A favor": prob_base += 0.18
    elif f_blood == "En contra": prob_base -= 0.18
    if eco_adv == "Full Buy vs Eco": prob_base += 0.25
    elif eco_adv == "Eco vs Full Buy": prob_base -= 0.25

    return max(0.05, min(0.95, prob_base))

# ==========================================
# 4. TEMAS Y CSS
# ==========================================
st.sidebar.markdown("### 🎨 Apariencia")
tema = st.sidebar.selectbox("", ["Azul Oscuro (Defecto)", "Verde Hacker", "Rojo Táctico"])

colors = {
    "Azul Oscuro (Defecto)": ("#0B1120", "#1E293B", "#F1F5F9", "#38BDF8"), 
    "Verde Hacker": ("#000000", "#051A05", "#4ADE80", "#10B981"), 
    "Rojo Táctico": ("#0A0000", "#1A0505", "#FECACA", "#EF4444")
}
c_bg, c_card, c_text, c_acc = colors[tema]
c_sub, c_border, c_btn = "#94A3B8", "#334155", "#0F172A"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {c_bg}; color: {c_text}; font-family: 'Inter', sans-serif; }}
    [data-testid="stSidebar"] {{ background-color: {c_card} !important; border-right: 1px solid {c_border}; }}
    .glass-card {{ background: {c_card}; border: 1px solid {c_border}; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); position: relative; }}
    .team-logo {{ width: 60px; height: 60px; object-fit: contain; margin-bottom: 5px; }}
    .winrate-text {{ font-size: 13px; color: {c_acc}; font-weight: 900; margin-bottom: 5px; background: {c_btn}; padding: 2px 8px; border-radius: 10px; display: inline-block; }}
    .tower-plate {{ width: 14px; height: 8px; border-radius: 2px; display: inline-block; margin:0 2px; }}
    .win {{ background-color: #10B981; }} .loss {{ background-color: #EF4444; }} .unknown {{ background-color: #475569; }}
    .prob-box {{ background: {c_btn}; padding: 15px; border-radius: 8px; border: 1px solid {c_acc}; text-align: center; margin-bottom: 15px; }}
    .prob-number {{ font-size: 32px; font-weight: 900; color: {c_acc}; }}
    .sniper-alert {{ background: rgba(16, 185, 129, 0.15); border: 2px dashed #10B981; padding: 15px; border-radius: 8px; margin: 15px 0; text-align: center; color: #10B981; font-weight: bold; animation: pulse 1.5s infinite; }}
    .badge-live {{ background: #EF4444; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; animation: pulse 2s infinite; }}
    .badge-time {{ background: {c_acc}; color: {c_bg}; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; }}
    .stream-btn {{ background-color: #9146FF; color: white !important; padding: 8px 12px; border-radius: 8px; text-decoration: none; font-size: 12px; font-weight: bold; display: block; margin-top: 15px; text-align: center; transition: 0.2s; width: 100%; }}
    .stream-btn:hover {{ background-color: #772CE8; transform: scale(1.02); }}
    div.stButton > button {{ background-color: {c_btn}; color: {c_acc}; border: 1px solid {c_border}; font-weight: bold; border-radius: 8px; padding: 10px; }}
    [data-testid="stExpanderDetails"] {{ padding-bottom: 180px !important; }}
    @keyframes pulse {{ 0% {{opacity: 1;}} 50% {{opacity: 0.6;}} 100% {{opacity: 1;}} }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. SIDEBAR Y SISTEMA MAESTRO
# ==========================================
st.sidebar.markdown("---")
token_activo = False
try:
    if "token" in st.query_params and st.query_params["token"] == "capo": token_activo = True
except: pass

if token_activo: 
    st.sidebar.markdown("<div style='background-color:#10B981; color:white; padding:5px; border-radius:5px; text-align:center; font-weight:bold; font-size:12px; margin-bottom:10px;'>🔓 MODO CAPO ACTIVO</div>", unsafe_allow_html=True)

st.sidebar.markdown(f"<h2 style='color:{c_acc}; text-align:center;'>🏦 Mi Bankroll</h2>", unsafe_allow_html=True)
nuevo_bank = st.sidebar.number_input("Ajustar Saldo (U):", value=float(bank_actual), step=10.0)
if st.sidebar.button("💾 Guardar Saldo", use_container_width=True): gestionar_bank(nuevo_bank); st.rerun()
st.sidebar.markdown(f"<h1 style='text-align:center; color:{c_text};'>{bank_actual:.2f} U</h1>", unsafe_allow_html=True)

st.sidebar.markdown("---")
categoria = st.sidebar.radio("🌐 TIPO DE OPERACIÓN", ["⚔️ MOBAs (Estrategia)", "🔫 Shooters (Tácticos)"])
st.sidebar.markdown("---")

mercados_fps = [
    "-- Seleccione un Mercado --", 
    "⭐ PARTIDO: Ganador del Partido", 
    "⭐ PARTIDO: Handicap de Mapas", 
    "⭐ PARTIDO: Total de Mapas (O/U)", 
    "🗺️ MAPA: Ganador", 
    "🗺️ MAPA: Handicap de Rondas", 
    "🗺️ MAPA: Total de Rondas (O/U)", 
    "🗺️ MAPA: Carrera a 5 Rondas", 
    "🗺️ MAPA: Carrera a 9 Rondas", 
    "🗺️ MAPA: Carrera a 13 Rondas",
    "🗺️ MAPA: Ronda de Pistolas (R1/R13)"
]

if categoria == "⚔️ MOBAs (Estrategia)":
    # PARCHE: Cambiado 'mobile-legends' a 'mlbb' en el diccionario para la API
    juegos_config = {
        "League of Legends": {"slug": "lol", "mercados": ["-- Seleccione un Mercado --", "⭐ PARTIDO: Ganador del Partido", "Handicap", "Primera Sangre", "Primer Dragón", "Carrera a 5 Kills", "Carrera a 10 Kills", "Carrera a 15 Kills", "Total Dragones", "Total Barones", "Total Torres", "Total Kills", "Kills por Equipo", "Duración de Partida"]},
        "Dota 2": {"slug": "dota2", "mercados": ["-- Seleccione un Mercado --", "⭐ PARTIDO: Ganador del Partido", "Handicap", "Primer Roshan", "Carrera a 5 Kills", "Carrera a 10 Kills", "Carrera a 15 Kills", "Total Torres", "Total Kills", "Kills por Equipo", "Duración de Partida"]},
        "Mobile Legends": {"slug": "mlbb", "mercados": ["-- Seleccione un Mercado --", "⭐ PARTIDO: Ganador del Partido", "Handicap", "Primer Lord", "Carrera a 5 Kills", "Carrera a 10 Kills", "Carrera a 15 Kills", "Total Kills", "Kills por Equipo", "Duración de Partida"]}
    }
else:
    juegos_config = {
        "CS:GO 2": {"slug": "csgo", "mercados": mercados_fps},
        "Valorant": {"slug": "valorant", "mercados": mercados_fps}
    }

st.sidebar.markdown(f"<h3 style='color:{c_text};'>🎮 Disciplina</h3>", unsafe_allow_html=True)
juego_sel = st.sidebar.radio("", list(juegos_config.keys()))
slug = juegos_config[juego_sel]["slug"]
mercados_list = juegos_config[juego_sel]["mercados"]

if st.sidebar.button("🗑️ Limpiar Caché", use_container_width=True): st.cache_data.clear(); st.rerun()

# ==========================================
# 6. RADAR QUANT CORE
# ==========================================
st.markdown(f"<h2 style='color:{c_text};'>📡 Radar Quant: {juego_sel}</h2>", unsafe_allow_html=True)
    
running = call_api_live(slug, "matches/running", "per_page=10")
upcoming = call_api_live(slug, "matches/upcoming", "per_page=30&sort=begin_at")
partidos_totales = running + upcoming

hoy_utc = datetime.utcnow()
hoy_local = hoy_utc - timedelta(hours=4)
str_hoy_local = hoy_local.strftime("%Y-%m-%d")
str_mañana_local = (hoy_local + timedelta(days=1)).strftime("%Y-%m-%d")

partidos_filtrados = []
for p in partidos_totales:
    if p['status'] == 'running':
        partidos_filtrados.append(p)
    elif p['status'] == 'not_started' and p.get('begin_at'):
        dt_utc = datetime.strptime(p['begin_at'], "%Y-%m-%dT%H:%M:%SZ")
        dt_local = dt_utc - timedelta(hours=4)
        if dt_local.strftime("%Y-%m-%d") in [str_hoy_local, str_mañana_local]:
            partidos_filtrados.append(p)

if not partidos_filtrados: st.info("Escaneando servidores. No hay actividad oficial inmediata en las próximas 48 horas.")
else:
    c1, c2 = st.columns(2)
    for i, m in enumerate(partidos_filtrados[:16]):
        opp = m.get('opponents', [])
        if len(opp) < 2: continue
        t1, t2 = opp[0]['opponent'], opp[1]['opponent']
        
        _, wr1, form1 = fetch_historical_data(slug, t1['id'])
        _, wr2, form2 = fetch_historical_data(slug, t2['id'])

        if m['status'] == 'running':
            badge = "<span class='badge-live'>🔴 EN VIVO</span>"
        else:
            dt_utc = datetime.strptime(m['begin_at'], "%Y-%m-%dT%H:%M:%SZ")
            dt_local = dt_utc - timedelta(hours=4)
            if dt_local.strftime("%Y-%m-%d") == str_hoy_local:
                badge = f"<span class='badge-time'>🕒 Hoy {dt_local.strftime('%H:%M')}</span>"
            else:
                badge = f"<span class='badge-time'>📅 {dt_local.strftime('%d/%m')} 🕒 {dt_local.strftime('%H:%M')}</span>"

        stream_link = m.get('official_video_url')
        if not stream_link and m.get('streams_list'):
            stream_link = m['streams_list'][0].get('raw_url', '')
        boton_stream = f'<a href="{stream_link}" target="_blank" class="stream-btn">📺 Ver Transmisión Oficial</a>' if stream_link else ''

        with (c1 if i % 2 == 0 else c2):
            st.markdown(f"""
            <div class="glass-card">
                <div style="margin-bottom: 10px; font-size: 11px; display: flex; justify-content: space-between;"><span>🏆 {m['league']['name']}</span>{badge}</div>
                <div style="display: flex; justify-content: space-around; align-items: center; text-align: center;">
                    <div style="width: 40%;"><div style="font-size:12px; font-weight:bold;">{t1['name']}</div><img src="{t1.get('image_url','')}" class="team-logo"><br><div class="winrate-text">{wr1*100:.0f}%</div><div>{"".join([f"<div class='tower-plate {x}'></div>" for x in form1])}</div></div>
                    <div style="font-size: 20px; font-weight: bold; color: {c_acc};">VS</div>
                    <div style="width: 40%;"><div style="font-size:12px; font-weight:bold;">{t2['name']}</div><img src="{t2.get('image_url','')}" class="team-logo"><br><div class="winrate-text">{wr2*100:.0f}%</div><div>{"".join([f"<div class='tower-plate {x}'></div>" for x in form2])}</div></div>
                </div>
                {boton_stream}
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"⚙️ Analítica y Operación"):
                sel_mer = st.selectbox("Mercado:", mercados_list, key=f"mer_{i}")
                
                if sel_mer != "-- Seleccione un Mercado --":
                    c_izq, c_der = st.columns(2)
                    with c_izq:
                        if "Total" in sel_mer or "Duración" in sel_mer: 
                            sel_opcion = st.radio("Opción:", ["Más (+)", "Menos (-)"], horizontal=True, key=f"op_{i}")
                        else: 
                            sel_opcion = st.radio("A favor de:", [t1['name'], t2['name']], horizontal=True, key=f"op_{i}")
                        linea = st.number_input("Línea de Casino:", value=0.0, step=0.5, key=f"l_{i}")
                    
                    with c_der:
                        st.write("")
                        prob_final = 0.50
                        ajuste_mapa_2 = 0
                        
                        if "PARTIDO" not in sel_mer:
                            st.markdown(f"<div style='border-top:1px solid {c_border}; margin-top:5px; padding-top:5px;'></div>", unsafe_allow_html=True)
                            mapa_context = st.radio("📍 Operando en:", ["Mapa 1", "Mapa 2 (o posterior)"], horizontal=True, key=f"ctx_{i}")
                            
                            if mapa_context == "Mapa 2 (o posterior)":
                                st.markdown(f"<p style='font-size:11px; color:{c_acc}; font-weight:bold;'>🔁 Inyector Momentum (Ganador Mapa Anterior)</p>", unsafe_allow_html=True)
                                res_m1 = st.selectbox("", ["Ninguno", t1['name'], t2['name']], key=f"m1_{i}")
                                
                                if res_m1 != "Ninguno":
                                    es_t1_fav = wr1 >= wr2
                                    if "Total" in sel_mer or "Duración" in sel_mer:
                                        ajuste_mapa_2 = +0.03 if "Más" in sel_opcion else -0.03
                                    else:
                                        if res_m1 == t1['name']: 
                                            if sel_opcion == t1['name']: ajuste_mapa_2 = -0.02 if es_t1_fav else 0.01
                                            elif sel_opcion == t2['name']: ajuste_mapa_2 = 0.02 if es_t1_fav else -0.01
                                        elif res_m1 == t2['name']: 
                                            if sel_opcion == t2['name']: ajuste_mapa_2 = -0.02 if not es_t1_fav else 0.01
                                            elif sel_opcion == t1['name']: ajuste_mapa_2 = 0.02 if not es_t1_fav else -0.01
                                        
                        # MOTOR MOBA
                        if categoria == "⚔️ MOBAs (Estrategia)":
                            if "PARTIDO" not in sel_mer:
                                remontada = st.checkbox("💸 Modelo Oro (En Vivo)", key=f"rem_{i}")
                                ajuste_oro = 0
                                if remontada:
                                    c_min, c_oro = st.columns(2)
                                    min_actual = c_min.number_input("Min:", value=15, key=f"min_{i}")
                                    diff_oro = c_oro.number_input("Oro Diff:", value=0, step=500, key=f"oro_{i}")
                                    ajuste_oro = calculate_gold_impact(diff_oro, min_actual, slug)
                            else: ajuste_oro = 0 
                            
                            prob_base = motor_moba(wr1, wr2, sel_mer, sel_opcion, linea, t1['name'])
                            prob_final = max(0.05, min(0.95, prob_base + ajuste_oro + ajuste_mapa_2))
                        
                        # MOTOR FPS
                        else:
                            st.markdown(f"<div style='border-top:1px solid {c_border}; margin-top:5px; padding-top:5px;'></div>", unsafe_allow_html=True)
                            st.markdown("<p style='font-size:11px; color:#10B981;'>🎯 Simulador Bayesiano In-Play</p>", unsafe_allow_html=True)
                            f_blood = st.selectbox("Primera Sangre (Ronda):", ["Neutral", "A favor", "En contra"], key=f"fb_{i}")
                            eco_adv = st.selectbox("Economía (Armas):", ["Igualados", "Full Buy vs Eco", "Eco vs Full Buy"], key=f"eco_{i}")
                            prob_base = motor_fps(wr1, wr2, sel_mer, sel_opcion, linea, t1['name'], f_blood, eco_adv)
                            prob_final = max(0.05, min(0.95, prob_base + ajuste_mapa_2))

                    st.markdown(f"""
                    <div class="prob-box">
                        <div style="font-size:10px; text-transform:uppercase;">Probabilidad Algoritmo</div>
                        <div class="prob-number">{prob_final*100:.1f}%</div>
                        <div style="font-size:10px; color:{c_sub};">Cuota Mínima: {1/prob_final:.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if 0.75 <= prob_final <= 0.99:
                        st.markdown(f"<div class='sniper-alert'>🎯 ¡SNIPER ALERT!</div>", unsafe_allow_html=True)

                    cuota = st.number_input("Cuota Casino:", value=1.00, step=0.01, key=f"c_{i}")
                    if cuota > 1.01: 
                        if cuota > (1/prob_final):
                            kelly = (((cuota - 1) * prob_final) - (1 - prob_final)) / (cuota - 1)
                            stake = (kelly * 0.25) * bank_actual
                            if stake > 0:
                                st.success(f"🔥 Sugerido: {stake:.2f} U")
                                if st.button("Registrar", key=f"btn_{i}", use_container_width=True):
                                    gestionar_bank(bank_actual - stake)
                                    st.rerun()
                        else: st.warning("❌ Cuota sin valor.")