import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import requests
from math import exp, factorial
from datetime import datetime, timezone, timedelta

# ----------------------------- Configuration -----------------------------
st.set_page_config(page_title="Apex Terminal", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

AMB, TEAL, CORAL, STEEL = "#F5B942", "#2DD4BF", "#FB7185", "#7C9CFF"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
.stApp{background:#0A1020;color:#E6EAF2;font-family:'IBM Plex Sans',sans-serif;font-variant-numeric:tabular-nums}
.block-container{padding-top:1.2rem!important;max-width:1550px}
h1,h2,h3,h4,h5{font-family:'Sora',sans-serif!important;letter-spacing:-.01em;font-weight:600!important}
section[data-testid=stSidebar]{background:#0D1426;border-right:1px solid #1C2740}
.masthead{display:flex;justify-content:space-between;align-items:flex-end;padding:4px 0 14px;border-bottom:1px solid #1C2740;margin-bottom:10px}
.masthead h1{margin:0;font-size:2rem}.masthead p{margin:2px 0 0;color:#8A97B3;font-size:.9rem}
.pill{padding:3px 10px;border-radius:6px;font-size:.78rem;font-weight:600;border:1px solid #F5B94266;color:#F5B942;background:#F5B94214}
.ticker{overflow:hidden;white-space:nowrap;border-bottom:1px solid #1C2740;padding:7px 0;margin-bottom:16px;color:#A9B4CC;font-size:.85rem}
.ticker div{display:inline-block;padding-left:100%;animation:tick 45s linear infinite}
@keyframes tick{to{transform:translateX(-100%)}}
.signal{border-left:4px solid #F5B942;background:linear-gradient(90deg,#F5B94218,transparent);padding:14px 18px;border-radius:0 6px 6px 0;margin:6px 0 18px}
.signal b{font:700 1.35rem 'Sora'}.signal span{color:#B9C3DA}
.stat{padding:6px 14px;border-left:2px solid #1C2740;background:#0F182C;border-radius:4px;height:100%}
.stat .l{color:#8A97B3;font-size:.78rem;font-weight:500}.stat .v{font:600 1.45rem 'Sora';margin:2px 0}.stat .s{color:#6F7C99;font-size:.75rem}
.up .v{color:#2DD4BF}.down .v{color:#FB7185}.warn .v{color:#F5B942}
.stTabs [data-baseweb=tab-list]{gap:4px;border-bottom:1px solid #1C2740}
.stTabs [data-baseweb=tab]{padding:10px 18px;color:#8A97B3}
.stTabs [aria-selected=true]{color:#F5B942!important;font-weight:600}
.stTabs [data-baseweb=tab-highlight]{background:#F5B942!important;height:3px}
</style>""", unsafe_allow_html=True)

# ----------------------------- Helpers & Math -----------------------------
def stat(col, label, value, sub="", tone=""):
    col.markdown(f'<div class="stat {tone}"><div class="l">{label}</div><div class="v">{value}</div>'
                 f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)

def style(fig, h=280, legend=True):
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=h,
                      font=dict(color="#B9C3DA", family="IBM Plex Sans"), margin=dict(l=10, r=10, t=25, b=10),
                      showlegend=legend, legend=dict(orientation="h", y=1.15, x=0))
    fig.update_xaxes(gridcolor="#1C2740", zeroline=False)
    fig.update_yaxes(gridcolor="#1C2740", zeroline=False)
    return fig

def show(fig):
    st.plotly_chart(fig, use_container_width=True)

def table(df):
    st.dataframe(df, use_container_width=True, hide_index=True)

def poisson_matrix(xh, xa, n=8):
    ph = np.array([exp(-xh) * xh ** k / factorial(k) for k in range(n)])
    pa = np.array([exp(-xa) * xa ** k / factorial(k) for k in range(n)])
    m = np.outer(ph, pa)
    return m / m.sum()

@st.cache_data(ttl=600, show_spinner=False)
def get_json(url):
    try:
        r = requests.get(url, headers={"User-Agent": "apex-terminal/4.0"}, timeout=8)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def load_chess(platform, user):
    u = user.strip().lower()
    if platform == "Chess.com":
        s = get_json(f"https://api.chess.com/pub/player/{u}/stats")
        if not s: return None
        modes = {k: s.get(f"chess_{k}", {}) for k in ("bullet", "blitz", "rapid")}
        rec = {"win": 0, "loss": 0, "draw": 0}
        for v in modes.values():
            for k in rec: rec[k] += v.get("record", {}).get(k, 0)
        hist, arc = {}, get_json(f"https://api.chess.com/pub/player/{u}/games/archives")
        if arc and arc.get("archives"):
            g = get_json(arc["archives"][-1]) or {}
            rows = []
            for x in g.get("games", []):
                side = "white" if x["white"]["username"].lower() == u else "black"
                rows.append((x["time_class"], pd.to_datetime(x["end_time"], unit="s"), x[side]["rating"]))
            df = pd.DataFrame(rows, columns=["tc", "date", "rating"])
            hist = {k: v[["date", "rating"]] for k, v in df.groupby("tc")}
        return dict(ratings={k: v.get("last", {}).get("rating") for k, v in modes.items()},
                    best={k: v.get("best", {}).get("rating") for k, v in modes.items()},
                    rec=rec, puzzle=s.get("tactics", {}).get("highest", {}).get("rating"), hist=hist)
    d = get_json(f"https://lichess.org/api/user/{u}")
    if not d: return None
    perfs, c = d.get("perfs", {}), d.get("count", {})
    hist = {}
    for item in get_json(f"https://lichess.org/api/user/{u}/rating-history") or []:
        pts = [(pd.Timestamp(year=p[0], month=p[1] + 1, day=p[2]), p[3]) for p in item["points"]]
        hist[item["name"].lower()] = pd.DataFrame(pts, columns=["date", "rating"])
    return dict(ratings={k: perfs.get(k, {}).get("rating") for k, v in perfs.items() if k in ("bullet", "blitz", "rapid")},
                best={}, rec={"win": c.get("win", 0), "loss": c.get("loss", 0), "draw": c.get("draw", 0)},
                puzzle=perfs.get("puzzle", {}).get("rating"), hist=hist)

# ----------------------------- Base de données dynamique -----------------------------
AXES = ["Attaque", "Défense", "Possession", "Physique", "Transition"]
KELLY = {"Conservateur": 0.10, "Modéré": 0.25, "Agressif": 0.50}

# Base de données multi-championnats
DATABASE_MATCHES = {
    "Ligue 1": {
        "PSG – OM": dict(h="PSG", a="OM", xh=2.35, xa=1.15, odds=(1.95, 3.70, 4.60), poss=(64.2, 48.0), sot=(7.1, 3.8), fouls=(9.4, 14.2), cs=(50, 20), form=("V V N V V", "D V N D V"), power=([85, 78, 92, 64, 88], [70, 65, 55, 78, 60]), notes=("OM : Balerdi suspendu", "PSG : Effectif complet")),
        "Monaco – Lyon": dict(h="Monaco", a="Lyon", xh=1.90, xa=1.40, odds=(2.10, 3.60, 3.20), poss=(55.0, 52.0), sot=(5.8, 4.5), fouls=(11.0, 12.5), cs=(30, 25), form=("V D V V N", "V V D N D"), power=([80, 70, 75, 70, 82], [75, 68, 72, 68, 76]), notes=("Monaco fort à domicile", "Lyon irrégulier en déplacement"))
    },
    "Bundesliga": {
        "Bayern Munich – Borussia Dortmund": dict(h="Bayern", a="Dortmund", xh=2.60, xa=1.30, odds=(1.55, 4.80, 5.20), poss=(66.0, 51.0), sot=(8.2, 4.1), fouls=(8.5, 11.0), cs=(45, 25), form=("V V V D V", "V N V D V"), power=([92, 80, 90, 75, 88], [78, 70, 74, 76, 80]), notes=("Bayern : Attaque en feu", "Dortmund : Défense centrale fragilisée")),
        "Bayer Leverkusen – RB Leipzig": dict(h="Leverkusen", a="Leipzig", xh=2.10, xa=1.50, odds=(1.90, 3.80, 3.70), poss=(61.0, 53.0), sot=(6.5, 5.0), fouls=(10.0, 12.0), cs=(40, 35), form=("V V V V N", "D V V N V"), power=([86, 82, 85, 78, 85], [80, 76, 78, 80, 82]), notes=("Match très tactique", "Excellente transition des deux côtés"))
    },
    "Premier League": {
        "Arsenal – Manchester City": dict(h="Arsenal", a="City", xh=1.70, xa=1.75, odds=(2.70, 3.40, 2.55), poss=(55.0, 61.0), sot=(5.0, 5.9), fouls=(10.5, 9.0), cs=(40, 38), form=("V N V V D", "V V N V V"), power=([80, 86, 78, 82, 76], [90, 78, 92, 74, 88]), notes=("Arsenal : Retour de titulaire", "City : Rotation probable")),
        "Liverpool – Chelsea": dict(h="Liverpool", a="Chelsea", xh=2.20, xa=1.20, odds=(1.75, 4.00, 4.20), poss=(58.0, 54.0), sot=(6.8, 4.2), fouls=(11.0, 13.0), cs=(38, 28), form=("V V D V V", "N V D V N"), power=([88, 78, 82, 84, 86], [76, 72, 78, 72, 75]), notes=("Anfield est un fort", "Chelsea cherche de la stabilité"))
    },
    "La Liga": {
        "Real Madrid – FC Barcelone": dict(h="Real", a="Barça", xh=1.85, xa=1.60, odds=(2.15, 3.60, 3.30), poss=(52.0, 60.5), sot=(5.2, 5.6), fouls=(11.8, 10.1), cs=(35, 30), form=("V V V N V", "V D V V N"), power=([88, 74, 70, 80, 90], [84, 70, 88, 66, 82]), notes=("Real : Milieu physique", "Barça : Possession haute"))
    }
}

OPENINGS = {
    "Système Londres": dict(moves="1.d4 d5 2.Ff4", eco="D02", w=54, d=28, b=18, level="Débutant", style="Positionnel", plans=["Contrôler e5", "Structure d4-e3-c3", "Lever c4 ou e4"], trap="Abonner le pion b2."),
    "Défense Sicilienne": dict(moves="1.e4 c5", eco="B20", w=52, d=24, b=24, level="Avancé", style="Tactique", plans=["Contre-jeu aile dame", "Ouvrir colonne c", "Asymétrie"], trap="Théorie dense."),
    "Gambit Dame": dict(moves="1.d4 d5 2.c4", eco="D06", w=55, d=29, b=16, level="Intermédiaire", style="Positionnel", plans=["Pression d5", "Centre fort", "Développer Cd3/Cf3"], trap="Pion c4 récupérable."),
    "Défense Caro-Kann": dict(moves="1.e4 c6", eco="B10", w=50, d=30, b=20, level="Intermédiaire", style="Solide", plans=["Sortir le fou c8", "Structure saine", "Bons fous"], trap="Attaque Panov."),
    "Partie Italienne": dict(moves="1.e4 e5 2.Cf3 Cc6 3.Fc4", eco="C50", w=48, d=30, b=22, level="Débutant", style="Classique", plans=["Développement rapide", "Préparer c3-d4", "Attaque f7"], trap="Fried Liver.")
}

# ----------------------------- Barre latérale -----------------------------
st.sidebar.markdown("## ⚡ Apex Terminal")
st.sidebar.caption("v4.2 · Plateforme Quantitative Sports & Échecs")
st.sidebar.divider()

st.sidebar.markdown("#### 🌍 Sélection Compétition")
LEAGUES = {
    "⚽ Football": ["Ligue 1", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue des champions"],
    "🎾 Tennis": ["ATP Masters 1000", "WTA 1000", "Grand Chelem"],
    "🏀 Basketball": ["NBA", "EuroLeague", "Betclic Élite"], 
    "⚾ Baseball": ["MLB", "NPB"]
}
sport = st.sidebar.selectbox("Sport", list(LEAGUES))
league = st.sidebar.selectbox("Championnat", LEAGUES[sport])

st.sidebar.divider()
st.sidebar.markdown("#### ♟️ Configuration Échecs")
platform = st.sidebar.selectbox("Plateforme", ["Chess.com", "Lichess"])
username = st.sidebar.text_input("Pseudo Joueur", placeholder="ex. hikaru")

st.sidebar.divider()
st.sidebar.markdown("#### ⚙️ Gestion Risque")
bankroll = st.sidebar.number_input("Capital (€)", 100, 1_000_000, 2500, 100)
risk = st.sidebar.select_slider("Profil Risk", list(KELLY), value="Modéré")

# ----------------------------- En-tête -----------------------------
st.markdown(f"""
<div class="masthead">
    <div>
        <h1>Apex Terminal Pro</h1>
        <p>Analyse quantitative : <b>{league}</b> sélectionné | Moteur d'échecs & Monte Carlo</p>
    </div>
    <span class="pill">Système actif · Live API Ready</span>
</div>
<div class="ticker">
    <div>🟢 Bayern 2-1 Dortmund (68') &nbsp;&nbsp;|&nbsp;&nbsp; PSG – OM : Cote 1.95 EV+ 12.4% &nbsp;&nbsp;|&nbsp;&nbsp; Arsenal – City : Poisson xG 3.45 &nbsp;&nbsp;|&nbsp;&nbsp; Modèle reconfiguré automatiquement</div>
</div>
""", unsafe_allow_html=True)

tab_sport, tab_chess, tab_open, tab_quant, tab_backtest = st.tabs([
    f"📊 Analyse {league}", "♟️ Station Échecs", "📚 Répertoire Ouvertures", "💼 Simulation & Portfolio", "📈 Backtesting & ROI"
])
# ----------------------------- Onglet 1 : Sport -----------------------------
with tab_sport:
    st.subheader(f"📊 Analyse des Paris — {league}")

    # --- FILTRE PAR DATE ---
    col_filter, _ = st.columns([2, 2])
    with col_filter:
        filtre_date = st.radio(
            "📅 Filtrer par date :",
            ["Tous", "Aujourd'hui", "Demain"],
            horizontal=True
        )

    st.write("")

    # Filtrage et affichage des matchs
    matchs_a_afficher = []
    maintenant = datetime.now(timezone.utc)
    aujourdhui_date = maintenant.date()
    demain_date = aujourdhui_date + timedelta(days=1)

    for m in match_data:
        # Conversion du timestamp API en objet datetime
        commence_str = m.get('commence_time', '')
        if commence_str:
            try:
                # Format ISO 8601 (ex: "2026-09-21T20:45:00Z")
                dt = datetime.fromisoformat(commence_str.replace('Z', '+00:00'))
                match_date = dt.date()
                date_lisible = dt.strftime("%d/%m/%Y à %H:%M")
            except Exception:
                match_date = aujourdhui_date
                date_lisible = "Heure N/A"
        else:
            match_date = aujourdhui_date
            date_lisible = "Aujourd'hui"

        # Application du filtre radio
        if filtre_date == "Aujourd'hui" and match_date != aujourdhui_date:
            continue
        elif filtre_date == "Demain" and match_date != demain_date:
            continue

        # Sauvegarde pour l'affichage
        m_copy = dict(m)
        m_copy['date_formatted'] = date_lisible
        matchs_a_afficher.append(m_copy)

    # Message si aucun match ne correspond au filtre
    if not matchs_a_afficher:
        st.info(f"ℹ️ Aucun match prévu **{filtre_date.lower()}** pour la ligue sélectionnée.")
    else:
        # Affichage des cartes de matchs
        for match in matchs_a_afficher:
            with st.container():
                st.markdown(f"#### ⚽ {match['home_team']} vs {match['away_team']}")
                st.caption(f"📅 **Date & Heure :** {match['date_formatted']}")

                # Affichage des cotes
                c1, c2, c3 = st.columns(3)
                c1.metric(f"Victoire {match['home_team']}", f"{match.get('home_odds', 1.0):.2f}")
                if 'draw_odds' in match and match['draw_odds']:
                    c2.metric("Match Nul", f"{match['draw_odds']:.2f}")
                c3.metric(f"Victoire {match['away_team']}", f"{match.get('away_odds', 1.0):.2f}")

                st.divider()

    # Contrôles interactifs du live et ajustements
    with st.expander("🛠️ Panneau de contrôle interactif (Live, xG & Cotes)", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        xh = c1.number_input(f"xG {m['h']}", 0.1, 5.0, m["xh"], 0.05)
        xa = c2.number_input(f"xG {m['a']}", 0.1, 5.0, m["xa"], 0.05)
        o1 = c3.number_input(f"Cote {m['h']}", 1.01, 30.0, m["odds"][0], 0.05)
        oX = c4.number_input("Cote Nul", 1.01, 30.0, m["odds"][1], 0.05)
        o2 = c5.number_input(f"Cote {m['a']}", 1.01, 30.0, m["odds"][2], 0.05)

    # Calculs du Modèle de Poisson
    M = poisson_matrix(xh, xa)
    probs = [np.tril(M, -1).sum(), np.trace(M), np.triu(M, 1).sum()]
    odds, labels = [o1, oX, o2], [m["h"], "Nul", m["a"]]
    imp = np.array([1 / o for o in odds])
    fair = imp / imp.sum()
    ev = [p * o - 1 for p, o in zip(probs, odds)]
    k = int(np.argmax(ev))
    kelly = max(0.0, (probs[k] * odds[k] - 1) / (odds[k] - 1))
    stake = min(bankroll * kelly * KELLY[risk], bankroll * 0.05)
    idx = np.add.outer(range(M.shape[0]), range(M.shape[1]))

    if ev[k] > 0:
        st.markdown(f'<div class="signal"><b>⚡ Opportunité EV+ Détectée : {labels[k]} à {odds[k]:.2f}</b><br>'
                    f'<span>Probabilité modèle : <b>{probs[k]:.1%}</b> vs Marché : <b>{fair[k]:.1%}</b>. '
                    f'Esperance de gain : <b>{ev[k]:+.1%}</b>. Mise optimale (Kelly {risk}) : <b>{stake:.2f} €</b>.</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="signal" style="border-color:#8A97B3"><b>⚪ Pas de Value Bet identifié</b><br>'
                    '<span>Le marché est parfaitement ajusté ou surévalué par rapport au modèle de Poisson. Pas de prise de risque recommandée.</span></div>', unsafe_allow_html=True)

    s = st.columns(6)
    stat(s[0], f"Prob. {m['h']}", f"{probs[0]:.1%}", f"Marché: {fair[0]:.1%}", "up" if ev[0]>0 else "")
    stat(s[1], "Prob. Nul", f"{probs[1]:.1%}", f"Marché: {fair[1]:.1%}", "up" if ev[1]>0 else "")
    stat(s[2], f"Prob. {m['a']}", f"{probs[2]:.1%}", f"Marché: {fair[2]:.1%}", "up" if ev[2]>0 else "")
    stat(s[3], "Meilleur EV", f"{ev[k]:+.1%}", labels[k], "up" if ev[k] > 0 else "down")
    stat(s[4], "Total xG Match", f"{xh + xa:.2f}", "Plafond Buts", "warn")
    stat(s[5], "Mise Conseillée", f"{stake:.2f} €", f"{stake/bankroll:.1%} du Capital", "warn")

    st.write("")
    left, right = st.columns([3, 2])
    with left:
        st.markdown("##### 📈 Distribution Modèle vs Implicite Marché")
        fig = go.Figure([
            go.Bar(name="Modèle Poisson AI", x=labels, y=np.array(probs) * 100, marker_color=TEAL),
            go.Bar(name="Marché Bookmaker (Marge ajustée)", x=labels, y=fair * 100, marker_color=STEEL)
        ])
        fig.update_layout(barmode="group", yaxis_title="Probabilité (%)")
        show(style(fig, 260))

        st.markdown("##### 🎯 Probabilités des Marchés Annexes")
        table(pd.DataFrame({
            "Marché": ["Plus de 1,5 buts", "Plus de 2,5 buts", "Plus de 3,5 buts", "Les deux équipes marquent", "Clean Sheet " + m["h"]],
            "Probabilité": [f"{M[idx >= 2].sum():.1%}", f"{M[idx >= 3].sum():.1%}", f"{M[idx >= 4].sum():.1%}", f"{M[1:, 1:].sum():.1%}", f"{M[:, 0].sum():.1%}"],
            "Cote Juste Estimée": [f"{1 / max(v, 1e-6):.2f}" for v in (M[idx >= 2].sum(), M[idx >= 3].sum(), M[idx >= 4].sum(), M[1:, 1:].sum(), M[:, 0].sum())]
        }))

        st.markdown("##### 📊 Comparatif Statistique Équipes")
        table(pd.DataFrame({
            "Indicateur": ["xG moyen par match", "Possession moyenne (%)", "Tirs cadrés / match", "Fautes / match", "Clean sheets (%)", "Forme (5 derniers)"],
            m["h"]: [f"{xh:.2f}", m["poss"][0], m["sot"][0], m["fouls"][0], m["cs"][0], m["form"][0]],
            m["a"]: [f"{xa:.2f}", m["poss"][1], m["sot"][1], m["fouls"][1], m["cs"][1], m["form"][1]]
        }))

    with right:
        st.markdown("##### 🧮 Matrice des Scores Exacts Probables (Top 36)")
        z = M[:6, :6] * 100
        hm = go.Figure(go.Heatmap(z=z, x=list(range(6)), y=list(range(6)), colorscale=[[0, "#0F182C"], [1, AMB]], texttemplate="%{z:.1f}%", showscale=False))
        hm.update_layout(xaxis_title=f"Buts {m['a']}", yaxis_title=f"Buts {m['h']}", yaxis_autorange="reversed")
        show(style(hm, 280, False))

        st.markdown("##### ⚡ Radar des Forces Tactiques")
        rd = go.Figure()
        for team, vals, col in ((m["h"], m["power"][0], TEAL), (m["a"], m["power"][1], CORAL)):
            rd.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=AXES + AXES[:1], name=team, fill="toself", line_color=col))
        rd.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(visible=False)))
        show(style(rd, 240))

# ----------------------------- Onglet 2 : Échecs -----------------------------
with tab_chess:
    st.subheader("♟️ Station d'Analyse du Joueur")
    P = load_chess(platform, username) if username else None
    
    if not username:
        st.info("💡 Saisis ton pseudo dans la barre latérale pour charger automatiquement tes statistiques API.")
    elif not P:
        st.error(f"❌ Profil « {username} » introuvable sur {platform}.")
        
    if P:
        rec = P["rec"]
        tot = max(sum(rec.values()), 1)
        s = st.columns(5)
        for col, (key, lab) in zip(s[:3], (("bullet", "Bullet"), ("blitz", "Blitz"), ("rapid", "Rapide"))):
            stat(col, f"Elo {lab}", P["ratings"].get(key) or "N/A", f"Top : {P['best'].get(key) or '—'}", "up")
        stat(s[3], "Puzzles Elo", P["puzzle"] or "N/A", "Tactique")
        stat(s[4], "Victoires", f"{rec['win'] / tot:.1%}", f"{tot} parties", "warn")
        
        st.write("")
        a, b = st.columns(2)
        with a:
            st.markdown("##### 📈 Courbe de progression Elo")
            if P["hist"]:
                tc = st.selectbox("Cadence d'analyse", list(P["hist"]))
                df = P["hist"][tc]
                fig = px.line(df, x="date", y="rating", markers=len(df) < 60)
                fig.update_traces(line_color=AMB)
                show(style(fig, 280, False))
            else:
                st.info("Pas d'historique de parties récent trouvé.")
        with b:
            st.markdown("##### 📊 Ratio Victoires / Défaites / Nuls")
            fig = px.pie(names=["Victoires", "Défaites", "Nuls"], values=[rec["win"], rec["loss"], rec["draw"]], hole=0.55, color_discrete_sequence=[TEAL, CORAL, STEEL])
            show(style(fig, 280))

# ----------------------------- Onglet 3 : Ouvertures -----------------------------
with tab_open:
    st.subheader("📚 Encyclopédie & Matrice des Ouvertures")
    l, r = st.columns([1, 2])
    with l:
        pick = st.radio("Sélectionner une ouverture :", list(OPENINGS), format_func=lambda n: f"{n} ({OPENINGS[n]['eco']})")
        o = OPENINGS[pick]
        st.markdown(f"**Premier coups :** `{o['moves']}`")
        st.markdown(f"**Niveau conseillé :** {o['level']} | **Style :** {o['style']}")
        st.markdown("**Plans de développement :**\n" + "\n".join(f"- {p}" for p in o["plans"]))
        st.warning(f"⚠️ Piege classique : {o['trap']}")
    with r:
        s = st.columns(3)
        stat(s[0], "Win Rate Blancs", f"{o['w']} %", tone="up")
        stat(s[1], "Parties Nulle", f"{o['d']} %", tone="warn")
        stat(s[2], "Win Rate Noirs", f"{o['b']} %", tone="down")
        
        df = pd.DataFrame(OPENINGS).T.reset_index().rename(columns={"index": "Ouverture"})
        fig = px.bar(df, y="Ouverture", x=["w", "d", "b"], orientation="h", barmode="stack", color_discrete_sequence=[TEAL, AMB, CORAL])
        show(style(fig, 260))
        st.components.v1.iframe("https://lichess.org/tv/frame?theme=dark&bg=dark", height=300)

# ----------------------------- Onglet 4 : Monte Carlo & Quant -----------------------------
with tab_quant:
    st.subheader("💼 Simulation de Monte Carlo & Gestion du Capital")
    c = st.columns(5)
    n_bets = c[0].slider("Nombre de paris", 20, 500, 100)
    n_sims = c[1].slider("Simulations", 100, 2000, 500)
    p_win = c[2].slider("Taux de réussite (%)", 20, 80, 53) / 100
    avg_odds = c[3].slider("Cote moyenne", 1.2, 4.0, 1.95)
    frac = c[4].slider("Mise (% Capital)", 0.5, 10.0, 2.0) / 100

    rng = np.random.default_rng(42)
    growth = np.where(rng.random((n_bets, n_sims)) < p_win, 1 + frac * (avg_odds - 1), 1 - frac)
    paths = bankroll * np.cumprod(growth, axis=0)
    full = np.vstack([np.full(n_sims, bankroll), paths])
    final = paths[-1]

    s = st.columns(4)
    stat(s[0], "Avantage/Pari (Edge)", f"{(p_win * avg_odds - 1):+.1%}", tone="up" if (p_win * avg_odds - 1)>0 else "down")
    stat(s[1], "Capital Final Médian", f"{np.median(final):,.0f} €", tone="up")
    stat(s[2], "Probabilité de Profit", f"{(final > bankroll).mean():.0%}", tone="warn")
    stat(s[3], "Risque Ruine (>50% perte)", f"{(full.min(axis=0) < bankroll / 2).mean():.1%}", tone="down")

    st.write("")
    g1, g2 = st.columns([3, 2])
    with g1:
        st.markdown("##### 📈 Trajectoires de Capital Simulées")
        x = list(range(n_bets + 1))
        p10, p50, p90 = (np.percentile(full, q, axis=1) for q in (10, 50, 90))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=p90, line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=p10, fill="tonexty", fillcolor="rgba(124,156,255,.18)", line=dict(width=0), name="80% des scénarios"))
        fig.add_trace(go.Scatter(x=x, y=p50, line=dict(color=AMB, width=3), name="Médiane"))
        show(style(fig, 300))
    with g2:
        st.markdown("##### 📊 Distribution du Capital Final")
        fig = px.histogram(x=final, nbins=30, color_discrete_sequence=[TEAL])
        fig.add_vline(x=bankroll, line_dash="dash", line_color=CORAL)
        show(style(fig, 300, False))
# ----------------------------- Onglet 5 : Backtesting & Historique -----------------------------
with tab_backtest:
    st.subheader("📈 Backtesting & Analyse des Performances Réelles")
    st.markdown("Importe ton fichier CSV de paris passés pour analyser ton rendement réel, ton Drawdown et ton Sharpe Ratio.")

    # Exemple de structure CSV attendue
    st.info("💡 **Format CSV attendu :** Colonnes `Date`, `Mise`, `Cote`, `Résultat` (valeurs de Résultat : `Gagné`, `Perdu`, `Remboursé`).")

    # Mode démo ou import utilisateur
    uploaded_file = st.file_uploader("Déposer un fichier CSV de vos paris", type=["csv"])

    if uploaded_file is not None:
        df_history = pd.read_csv(uploaded_file)
    else:
        st.warning("⚠️ Aucun fichier importé. Chargement d'un **jeu de données de démonstration (100 paris)**.")
        # Génération de données factices pour la démonstration
        np.random.seed(42)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='D')
        mises = np.random.choice([20, 50, 100], size=100)
        cotes = np.round(np.random.uniform(1.50, 2.80, size=100), 2)
        results = np.random.choice(["Gagné", "Perdu", "Remboursé"], size=100, p=[0.52, 0.45, 0.03])
        df_history = pd.DataFrame({"Date": dates, "Mise": mises, "Cote": cotes, "Résultat": results})

    # Calculs quantitatifs du Backtest
    if not df_history.empty:
        df_history["Profit_Pari"] = 0.0
        df_history.loc[df_history["Résultat"] == "Gagné", "Profit_Pari"] = df_history["Mise"] * (df_history["Cote"] - 1)
        df_history.loc[df_history["Résultat"] == "Perdu", "Profit_Pari"] = -df_history["Mise"]
        df_history["Profit_Cumulé"] = df_history["Profit_Pari"].cumsum()
        df_history["Capital"] = bankroll + df_history["Profit_Cumulé"]

        # Indicateurs clés de performance (KPIs)
        total_mises = df_history["Mise"].sum()
        total_profit = df_history["Profit_Pari"].sum()
        roi = (total_profit / total_mises) if total_mises > 0 else 0
        winrate = (df_history["Résultat"] == "Gagné").mean()

        # Calculation du Max Drawdown
        peak = df_history["Capital"].cummax()
        drawdown = (df_history["Capital"] - peak) / peak
        max_drawdown = drawdown.min()

        # Sharpe Ratio simplifié (sur rendement par pari)
        returns = df_history["Profit_Pari"] / df_history["Mise"]
        sharpe = (returns.mean() / returns.std()) * np.sqrt(100) if returns.std() != 0 else 0

        # Affichage des statistiques
        s = st.columns(5)
        stat(s[0], "Profit Total", f"{total_profit:+,.2f} €", tone="up" if total_profit >= 0 else "down")
        stat(s[1], "ROI Réel", f"{roi:+.2%}", tone="up" if roi >= 0 else "down")
        stat(s[2], "Win Rate", f"{winrate:.1%}", f"{len(df_history)} paris")
        stat(s[3], "Max Drawdown", f"{max_drawdown:.1%}", tone="down")
        stat(s[4], "Sharpe Ratio", f"{sharpe:.2f}", tone="warn")

        st.write("")
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.markdown("##### 📈 Graphique d'évolution du Capital (€)")
            fig = px.line(df_history, x="Date", y="Capital", markers=True)
            fig.update_traces(line_color=TEAL if total_profit >= 0 else CORAL)
            fig.add_hline(y=bankroll, line_dash="dash", line_color=STEEL, annotation_text="Capital Initial")
            show(style(fig, 300, False))

        with col_right:
            st.markdown("##### 📋 Historique Détaillé des Paris")
            table(df_history[["Date", "Mise", "Cote", "Résultat", "Profit_Pari"]].tail(10))
