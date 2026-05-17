"""
Observatorio COVID-19 · Veracruz
Dashboard epidemiológico construido sobre datos abiertos de la DGE.
Ejecutar: streamlit run dashboard.py
"""

import os
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Observatorio COVID-19 · Veracruz",
    layout="wide",
    initial_sidebar_state="expanded",
)

RUTA_DB = os.path.join(os.path.dirname(__file__), "covid_veracruz.db")

# ============================================================
# TOKENS DE DISEÑO
# ============================================================
INK         = "#0E1218"
SURFACE     = "#171C24"
SURFACE_2   = "#1F2530"
BORDER      = "#2A3140"
RULE        = "#3A4258"
CREAM       = "#F2EDE3"
COOL        = "#9AA3B5"
MUTED       = "#5A6478"

AMBER       = "#D4A574"
AMBER_HI    = "#E8C9A0"
AMBER_DIM   = "#8B6E47"
AMBER_FILL  = "rgba(212, 165, 116, 0.10)"

POSITIVE    = "#9CB58A"
NEGATIVE    = "#C28B7A"
NEG_FILL    = "rgba(194, 139, 122, 0.18)"

CHART_PALETTE = [
    "#D4A574", "#9AA3B5", "#E8C9A0", "#7088A8",
    "#A88555", "#B0A084", "#5A7088", "#F2EDE3",
]

MESES_ES = {
    "01": "ENE", "02": "FEB", "03": "MAR", "04": "ABR", "05": "MAY", "06": "JUN",
    "07": "JUL", "08": "AGO", "09": "SEP", "10": "OCT", "11": "NOV", "12": "DIC",
}

GRUPOS_EDAD = [(0, 9), (10, 19), (20, 29), (30, 39), (40, 49),
               (50, 59), (60, 69), (70, 79), (80, 120)]
GRUPOS_LABELS = ["0-9", "10-19", "20-29", "30-39", "40-49",
                 "50-59", "60-69", "70-79", "80+"]


# ============================================================
# CARGA
# ============================================================
@st.cache_data(show_spinner="Cargando base de datos...")
def cargar_datos(ruta: str):
    con = sqlite3.connect(ruta)
    casos = pd.read_sql(
        """
        SELECT c.*, m.nombre AS municipio
        FROM casos c
        LEFT JOIN municipios m ON m.clave = c.municipio_res
        """, con,
    )
    con.close()

    casos["fecha_sintomas"] = pd.to_datetime(casos["fecha_sintomas"], errors="coerce")
    casos["fecha_def"] = pd.to_datetime(casos["fecha_def"], errors="coerce")
    casos["año"] = casos["fecha_sintomas"].dt.year
    casos["semana"] = casos["fecha_sintomas"].dt.to_period("W").dt.start_time
    casos["grupo_edad"] = pd.cut(
        casos["edad"],
        bins=[g[0] for g in GRUPOS_EDAD] + [121],
        labels=GRUPOS_LABELS, right=False,
    )
    return casos


# ============================================================
# ESTILOS
# ============================================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,300..700,0..100&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'DM Sans', sans-serif;
        background-color: {INK};
        color: {CREAM};
    }}

    #MainMenu, footer {{visibility: hidden;}}

    .block-container {{
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        max-width: 1340px;
    }}

    [data-testid="stSidebar"] > div:first-child {{
        background-color: {SURFACE};
        padding-top: 2rem;
    }}

    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] div {{ color: {CREAM}; }}

    [data-testid="stSidebar"] label {{
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.2px !important;
        color: {MUTED} !important;
    }}

    .masthead {{
        border-bottom: 1px solid {BORDER};
        padding-bottom: 1.5rem;
    }}

    .masthead-id {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem; color: {AMBER};
        letter-spacing: 2.5px; text-transform: uppercase; margin: 0;
    }}

    .masthead-title {{
        font-family: 'Fraunces', serif; font-weight: 400; font-size: 2.6rem;
        letter-spacing: -1.5px; color: {CREAM}; margin: 0.3rem 0 0 0; line-height: 1;
    }}

    .masthead-deck {{
        font-family: 'DM Sans', sans-serif; font-style: italic; font-size: 0.95rem;
        color: {COOL}; margin: 0.6rem 0 0 0;
    }}

    .meta-bar {{
        display: flex; gap: 3rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem; color: {MUTED};
        text-transform: uppercase; letter-spacing: 1.5px;
        padding: 1rem 0; border-bottom: 1px solid {BORDER}; margin: 0 0 2rem 0;
    }}
    .meta-bar strong {{ color: {CREAM}; font-weight: 500; }}

    .kpi-grid {{
        display: grid; grid-template-columns: repeat(5, 1fr); gap: 0;
        border-top: 1px solid {BORDER}; border-bottom: 1px solid {BORDER};
        margin: 0 0 2rem 0;
    }}
    .kpi-cell {{
        padding: 1.75rem 1.25rem 1.75rem 0;
        border-right: 1px solid {BORDER};
    }}
    .kpi-cell:first-child {{ padding-left: 0; }}
    .kpi-cell:last-child {{ border-right: none; padding-right: 0; }}
    .kpi-cell-padded {{ padding-left: 1.25rem; }}

    .kpi-label {{
        font-family: 'DM Sans', sans-serif; font-size: 0.6rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 2px; color: {MUTED};
        margin: 0 0 0.75rem 0;
    }}
    .kpi-number {{
        font-family: 'Fraunces', serif; font-weight: 400; font-size: 2rem;
        line-height: 1; letter-spacing: -1.2px; color: {CREAM}; margin: 0;
        font-feature-settings: 'tnum';
    }}
    .kpi-number.neg {{ color: {NEGATIVE}; }}
    .kpi-unit {{
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: {MUTED};
        text-transform: uppercase; letter-spacing: 1.5px;
        margin: 0.75rem 0 0 0; display: flex; align-items: center; gap: 6px;
    }}
    .kpi-tick {{
        display: inline-block; width: 8px; height: 1px; background: {AMBER};
    }}

    .section-block {{ margin: 3rem 0 1.5rem 0; padding-top: 2rem; border-top: 1px solid {BORDER}; }}
    .section-meta {{ display: flex; align-items: baseline; gap: 1rem; margin-bottom: 0.5rem; }}
    .section-id {{
        font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: {AMBER};
        letter-spacing: 1.5px; text-transform: uppercase;
    }}
    .section-divider {{ flex: 1; height: 1px; background: {BORDER}; }}
    .section-headline {{
        font-family: 'Fraunces', serif; font-weight: 500; font-size: 1.75rem;
        line-height: 1.1; letter-spacing: -0.5px; color: {CREAM}; margin: 0.5rem 0 0 0;
    }}
    .section-deck {{
        font-family: 'DM Sans', sans-serif; font-size: 0.85rem;
        color: {COOL}; margin: 0.5rem 0 0 0;
    }}
    .subhead {{
        font-family: 'DM Sans', sans-serif; font-size: 0.65rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 2px; color: {AMBER};
        margin: 0.5rem 0 0.5rem 0;
    }}
    .subhead.muted {{ color: {MUTED}; }}

    .colophon {{
        margin-top: 4rem; padding-top: 1.5rem; border-top: 2px solid {RULE};
        display: flex; justify-content: space-between;
        font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: {MUTED};
        text-transform: uppercase; letter-spacing: 1.5px;
    }}

    .stDateInput input, .stSelectbox > div > div, .stMultiSelect > div > div {{
        background-color: {INK} !important; border: 1px solid {BORDER} !important;
        border-radius: 4px !important; color: {CREAM} !important;
        font-family: 'JetBrains Mono', monospace !important;
    }}
    span[data-baseweb="tag"] {{
        background-color: {AMBER_DIM} !important; color: {CREAM} !important;
        border-radius: 2px !important;
    }}
    .streamlit-expanderHeader {{
        background-color: transparent !important; border: 1px solid {BORDER} !important;
        border-radius: 4px !important; font-family: 'DM Sans', sans-serif !important;
        font-size: 0.75rem !important; text-transform: uppercase !important;
        letter-spacing: 1.5px !important; color: {CREAM} !important;
    }}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================
def apply_chart_style(fig, height=380):
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="DM Sans, sans-serif", color=CREAM, size=12),
        height=height, margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER,
                   tickfont=dict(color=COOL, size=10, family="JetBrains Mono, monospace"),
                   linecolor=BORDER, showgrid=False),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER,
                   tickfont=dict(color=COOL, size=10, family="JetBrains Mono, monospace"),
                   linecolor=BORDER, showgrid=True, gridwidth=1),
        legend=dict(font=dict(color=CREAM, size=11), bgcolor='rgba(0,0,0,0)'),
        hoverlabel=dict(bgcolor=SURFACE_2, bordercolor=BORDER,
                        font=dict(color=CREAM, family="JetBrains Mono, monospace", size=11)),
    )
    return fig


def section_header(section_id, title, subtitle):
    st.markdown(f"""
    <div class="section-block">
        <div class="section-meta">
            <span class="section-id">— {section_id}</span>
            <div class="section-divider"></div>
        </div>
        <p class="section-headline">{title}</p>
        <p class="section-deck">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def fmt_fecha(d):
    s = d.strftime("%d %m %Y").upper()
    p = s.split(" ")
    p[1] = MESES_ES.get(p[1], p[1])
    return " ".join(p)


# ============================================================
# VERIFICACIÓN
# ============================================================
if not os.path.exists(RUTA_DB):
    st.markdown(f"""
    <div style="text-align: center; padding: 4rem 2rem;">
        <p style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: {AMBER}; letter-spacing: 2px; text-transform: uppercase; margin: 0 0 1rem 0;">— BASE DE DATOS NO ENCONTRADA</p>
        <p style="font-family: 'Fraunces', serif; font-style: italic; font-size: 1.5rem; color: {CREAM}; margin: 0 0 1rem 0;">Falta generar covid_veracruz.db</p>
        <p style="font-family: 'DM Sans'; color: {COOL}; max-width: 520px; margin: 0 auto; line-height: 1.6;">
            Ejecuta primero <code style="color:{AMBER};">python descargar_datos.py</code> y luego
            <code style="color:{AMBER};">python preparar_datos.py</code> para construir la base.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


casos = cargar_datos(RUTA_DB)


# ============================================================
# CABECERA
# ============================================================
st.markdown(f"""
<div class="masthead">
    <p class="masthead-id">— Observatorio epidemiológico · Veracruz</p>
    <p class="masthead-title">COVID-19 · Veracruz</p>
    <p class="masthead-deck">Análisis nominal sobre datos abiertos de la Dirección General de Epidemiología, 2020-2023.</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# PANEL LATERAL
# ============================================================
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 0 0 1rem 0; border-bottom: 1px solid {BORDER}; margin-bottom: 1rem;">
        <p style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: {AMBER}; letter-spacing: 2px; text-transform: uppercase; margin: 0;">— Controles</p>
        <p style="font-family: 'Fraunces', serif; font-style: italic; font-size: 1.2rem; color: {CREAM}; margin: 0.3rem 0 0 0;">Filtros</p>
    </div>
    """, unsafe_allow_html=True)

    fecha_min = casos["fecha_sintomas"].min().date()
    fecha_max = casos["fecha_sintomas"].max().date()

    rango = st.date_input(
        "Rango de fechas (síntomas)",
        value=(fecha_min, fecha_max),
        min_value=fecha_min, max_value=fecha_max,
    )

    universo = st.selectbox(
        "Universo de análisis",
        options=["Solo confirmados", "Confirmados + sospechosos", "Todos los registros"],
        index=0,
    )

    sexos = st.multiselect(
        "Sexo",
        options=[s for s in ["Mujer", "Hombre"] if s in casos["sexo"].dropna().unique()],
        default=[s for s in ["Mujer", "Hombre"] if s in casos["sexo"].dropna().unique()],
    )


# ============================================================
# FILTRADO
# ============================================================
if isinstance(rango, tuple) and len(rango) == 2:
    f_ini, f_fin = pd.to_datetime(rango[0]), pd.to_datetime(rango[1])
else:
    f_ini, f_fin = pd.to_datetime(fecha_min), pd.to_datetime(fecha_max)

df = casos[
    (casos["fecha_sintomas"] >= f_ini)
    & (casos["fecha_sintomas"] <= f_fin)
    & (casos["sexo"].isin(sexos))
].copy()

if universo == "Solo confirmados":
    df = df[df["confirmado"] == 1]
elif universo == "Confirmados + sospechosos":
    df = df[df["clasificacion"].isin(["Confirmado", "Sospechoso"])]


# ============================================================
# META
# ============================================================
emitido = fmt_fecha(datetime.now())
p_ini = fmt_fecha(f_ini)
p_fin = fmt_fecha(f_fin)

st.markdown(f"""
<div class="meta-bar">
    <div>EMITIDO &nbsp;·&nbsp; <strong>{emitido}</strong></div>
    <div>PERIODO &nbsp;·&nbsp; <strong>{p_ini} → {p_fin}</strong></div>
    <div>FUENTE &nbsp;·&nbsp; <strong>DGE · Datos abiertos COVID-19</strong></div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# KPIs
# ============================================================
n_total = len(df)
n_def = int(df["es_defuncion"].sum())
n_hosp = int((df["tipo_paciente"] == "Hospitalizado").sum())
n_uci = int((df["uci"] == 1).sum())
cfr = (n_def / n_total * 100) if n_total > 0 else 0
tasa_hosp = (n_hosp / n_total * 100) if n_total > 0 else 0

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-cell">
        <p class="kpi-label">Registros</p>
        <p class="kpi-number">{n_total:,}</p>
        <p class="kpi-unit"><span class="kpi-tick"></span> En el filtro</p>
    </div>
    <div class="kpi-cell kpi-cell-padded">
        <p class="kpi-label">Defunciones</p>
        <p class="kpi-number neg">{n_def:,}</p>
        <p class="kpi-unit"><span class="kpi-tick"></span> Fallecidos</p>
    </div>
    <div class="kpi-cell kpi-cell-padded">
        <p class="kpi-label">Letalidad (CFR)</p>
        <p class="kpi-number neg">{cfr:.2f}%</p>
        <p class="kpi-unit"><span class="kpi-tick"></span> Sobre el universo</p>
    </div>
    <div class="kpi-cell kpi-cell-padded">
        <p class="kpi-label">Hospitalizados</p>
        <p class="kpi-number">{n_hosp:,}</p>
        <p class="kpi-unit"><span class="kpi-tick"></span> {tasa_hosp:.1f}% del total</p>
    </div>
    <div class="kpi-cell kpi-cell-padded">
        <p class="kpi-label">Ingresos a UCI</p>
        <p class="kpi-number">{n_uci:,}</p>
        <p class="kpi-unit"><span class="kpi-tick"></span> Cuidados intensivos</p>
    </div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.markdown(f"""
    <div style="text-align:center; padding: 3rem;">
        <p style="font-family: 'Fraunces', serif; font-style: italic; font-size: 1.5rem; color: {COOL};">
            Sin registros con los filtros actuales.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ============================================================
# 01 — CURVA EPIDÉMICA
# ============================================================
section_header(
    "GRÁFICA 01 / CURVA EPIDÉMICA",
    "Casos y defunciones por semana",
    "Inicio de síntomas agrupado por semana. Las defunciones se ubican por fecha de inicio de síntomas del caso fallecido.",
)

semanal = df.groupby("semana").agg(
    casos=("id_registro", "count"),
    defunciones=("es_defuncion", "sum"),
).reset_index()

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=semanal["semana"], y=semanal["casos"],
    name="Casos", mode="lines",
    line=dict(color=AMBER, width=1.5),
    fill="tozeroy", fillcolor=AMBER_FILL,
    hovertemplate="<b>Semana del %{x|%d %b %Y}</b><br>%{y:,} casos<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=semanal["semana"], y=semanal["defunciones"],
    name="Defunciones", mode="lines",
    line=dict(color=NEGATIVE, width=1.5),
    fill="tozeroy", fillcolor=NEG_FILL,
    yaxis="y2",
    hovertemplate="<b>Semana del %{x|%d %b %Y}</b><br>%{y:,} defunciones<extra></extra>",
))
fig = apply_chart_style(fig, height=380)
fig.update_layout(
    legend=dict(orientation="h", y=1.1, x=0),
    yaxis=dict(title=None),
    yaxis2=dict(overlaying="y", side="right", showgrid=False,
                tickfont=dict(color=NEGATIVE, size=10, family="JetBrains Mono, monospace")),
)
st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 02 — PIRÁMIDE DE EDAD + LETALIDAD POR EDAD
# ============================================================
section_header(
    "GRÁFICA 02 / DEMOGRAFÍA",
    "Pirámide poblacional y letalidad por grupo de edad",
    "Distribución por sexo y edad; letalidad (CFR) creciente con la edad.",
)

col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.markdown('<p class="subhead">— PIRÁMIDE DE CASOS</p>', unsafe_allow_html=True)
    pir = df.groupby(["grupo_edad", "sexo"], observed=True).size().unstack(fill_value=0)
    for s in ("Mujer", "Hombre"):
        if s not in pir.columns:
            pir[s] = 0
    pir = pir.reindex(GRUPOS_LABELS, fill_value=0)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        y=pir.index, x=-pir["Mujer"], name="Mujer",
        orientation="h", marker=dict(color=AMBER),
        hovertemplate="<b>%{y}</b><br>Mujeres: %{customdata:,}<extra></extra>",
        customdata=pir["Mujer"],
    ))
    fig2.add_trace(go.Bar(
        y=pir.index, x=pir["Hombre"], name="Hombre",
        orientation="h", marker=dict(color=COOL),
        hovertemplate="<b>%{y}</b><br>Hombres: %{x:,}<extra></extra>",
    ))
    fig2 = apply_chart_style(fig2, height=380)
    fig2.update_layout(
        barmode="overlay", bargap=0.2,
        xaxis=dict(showgrid=True, gridcolor=BORDER,
                   tickvals=[-pir["Mujer"].max(), 0, pir["Hombre"].max()],
                   ticktext=[f"{pir['Mujer'].max():,}", "0", f"{pir['Hombre'].max():,}"]),
        legend=dict(orientation="h", y=1.1, x=0),
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.markdown('<p class="subhead muted">— LETALIDAD POR GRUPO DE EDAD (%)</p>', unsafe_allow_html=True)
    cfr_edad = df.groupby("grupo_edad", observed=True).agg(
        n=("id_registro", "count"),
        d=("es_defuncion", "sum"),
    )
    cfr_edad["cfr"] = (cfr_edad["d"] / cfr_edad["n"] * 100).fillna(0)
    cfr_edad = cfr_edad.reindex(GRUPOS_LABELS)

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=cfr_edad.index, y=cfr_edad["cfr"],
        marker=dict(color=NEGATIVE),
        hovertemplate="<b>%{x} años</b><br>CFR %{y:.2f}%<br>%{customdata[0]:,} casos · %{customdata[1]:,} defunciones<extra></extra>",
        customdata=cfr_edad[["n", "d"]].values,
    ))
    fig3 = apply_chart_style(fig3, height=380)
    fig3.update_layout(bargap=0.3, xaxis=dict(showgrid=False), yaxis=dict(ticksuffix="%"))
    st.plotly_chart(fig3, use_container_width=True)


# ============================================================
# 03 — COMORBILIDADES
# ============================================================
section_header(
    "GRÁFICA 03 / FACTORES DE RIESGO",
    "Prevalencia de comorbilidades",
    "Porcentaje de pacientes con cada comorbilidad, separando el total de casos y las defunciones.",
)

COMORB_LABEL = {
    "hipertension": "Hipertensión",
    "diabetes": "Diabetes",
    "obesidad": "Obesidad",
    "tabaquismo": "Tabaquismo",
    "cardiovascular": "Cardiovascular",
    "renal_cronica": "Renal crónica",
    "asma": "Asma",
    "epoc": "EPOC",
    "inmusupr": "Inmunosupresión",
}

def prevalencia(sub: pd.DataFrame) -> dict:
    res = {}
    for k, lab in COMORB_LABEL.items():
        s = sub[k].dropna()
        res[lab] = (s == 1).mean() * 100 if len(s) > 0 else 0
    return res

p_total = prevalencia(df)
p_def = prevalencia(df[df["es_defuncion"] == 1])

orden = sorted(COMORB_LABEL.values(), key=lambda x: p_total[x])
v_total = [p_total[x] for x in orden]
v_def = [p_def[x] for x in orden]

fig4 = go.Figure()
fig4.add_trace(go.Bar(
    y=orden, x=v_total, name="Total de casos",
    orientation="h", marker=dict(color=AMBER_DIM),
    hovertemplate="<b>%{y}</b><br>Total casos: %{x:.1f}%<extra></extra>",
))
fig4.add_trace(go.Bar(
    y=orden, x=v_def, name="Defunciones",
    orientation="h", marker=dict(color=NEGATIVE),
    hovertemplate="<b>%{y}</b><br>Defunciones: %{x:.1f}%<extra></extra>",
))
fig4 = apply_chart_style(fig4, height=440)
fig4.update_layout(
    barmode="group", bargap=0.25,
    yaxis=dict(showgrid=False, tickfont=dict(color=CREAM, size=11, family="DM Sans, sans-serif")),
    xaxis=dict(ticksuffix="%", showgrid=True, gridcolor=BORDER),
    legend=dict(orientation="h", y=1.08, x=0),
)
st.plotly_chart(fig4, use_container_width=True)


# ============================================================
# 04 — TOP MUNICIPIOS + TIPO DE PACIENTE
# ============================================================
section_header(
    "GRÁFICA 04 / GEOGRAFÍA Y MANEJO",
    "Municipios con mayor incidencia y tipo de atención",
    "Los quince municipios de Veracruz con más casos y la distribución entre atención ambulatoria y hospitalaria.",
)

col_x, col_y = st.columns([3, 2], gap="large")

with col_x:
    st.markdown('<p class="subhead">— TOP 15 MUNICIPIOS</p>', unsafe_allow_html=True)
    top_mun = (
        df[df["municipio"].notna()]
        .groupby("municipio")
        .size()
        .nlargest(15)
        .sort_values()
    )

    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        y=top_mun.index, x=top_mun.values,
        orientation="h", marker=dict(color=AMBER, line=dict(width=0)),
        hovertemplate="<b>%{y}</b><br>%{x:,} casos<extra></extra>",
    ))
    fig5 = apply_chart_style(fig5, height=460)
    fig5.update_layout(
        yaxis=dict(showgrid=False, tickfont=dict(color=CREAM, size=11, family="DM Sans, sans-serif")),
        xaxis=dict(showgrid=True, gridcolor=BORDER),
    )
    st.plotly_chart(fig5, use_container_width=True)

with col_y:
    st.markdown('<p class="subhead muted">— TIPO DE ATENCIÓN</p>', unsafe_allow_html=True)
    tipo = df["tipo_paciente"].value_counts()
    fig6 = go.Figure()
    fig6.add_trace(go.Pie(
        labels=tipo.index, values=tipo.values,
        hole=0.72,
        marker=dict(colors=[AMBER, NEGATIVE, COOL], line=dict(color=INK, width=2)),
        textfont=dict(color=CREAM, size=11, family="JetBrains Mono, monospace"),
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value:,} casos<br>%{percent}<extra></extra>",
    ))
    fig6 = apply_chart_style(fig6, height=300)
    fig6.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=-0.05, x=0.1, font=dict(size=10)),
    )
    st.plotly_chart(fig6, use_container_width=True)

    st.markdown('<p class="subhead muted" style="margin-top:1.5rem;">— SEVERIDAD DEL CUADRO</p>', unsafe_allow_html=True)
    sev_total = len(df)
    sev_neum = int((df["neumonia"] == 1).sum())
    sev_int = int((df["intubado"] == 1).sum())
    sev = pd.DataFrame({
        "indicador": ["Neumonía", "UCI", "Intubación"],
        "n": [sev_neum, n_uci, sev_int],
    })
    sev["pct"] = sev["n"] / sev_total * 100

    fig7 = go.Figure()
    fig7.add_trace(go.Bar(
        x=sev["pct"], y=sev["indicador"],
        orientation="h",
        marker=dict(color=[AMBER, AMBER_HI, NEGATIVE]),
        text=[f"{p:.1f}%" for p in sev["pct"]],
        textposition="outside",
        textfont=dict(color=CREAM, size=11, family="JetBrains Mono, monospace"),
        hovertemplate="<b>%{y}</b><br>%{customdata:,} casos (%{x:.1f}%)<extra></extra>",
        customdata=sev["n"],
    ))
    fig7 = apply_chart_style(fig7, height=180)
    fig7.update_layout(
        yaxis=dict(showgrid=False, tickfont=dict(color=CREAM, size=11)),
        xaxis=dict(showgrid=True, gridcolor=BORDER, ticksuffix="%"),
        margin=dict(l=10, r=50, t=10, b=10),
    )
    st.plotly_chart(fig7, use_container_width=True)


# ============================================================
# 05 — ANEXO / REGISTROS
# ============================================================
st.markdown(f"""
<div class="section-block">
    <div class="section-meta">
        <span class="section-id">— ANEXO / REGISTROS</span>
        <div class="section-divider"></div>
    </div>
    <p class="section-headline">Datos detallados</p>
    <p class="section-deck">Registros nominales anonimizados de la DGE filtrados al periodo seleccionado.</p>
</div>
""", unsafe_allow_html=True)

with st.expander("Abrir registros"):
    cols = ["id_registro", "fecha_sintomas", "sexo", "edad", "municipio",
            "clasificacion", "tipo_paciente", "neumonia", "uci", "es_defuncion",
            "diabetes", "hipertension", "obesidad"]
    st.dataframe(
        df[cols].sort_values("fecha_sintomas", ascending=False).head(300),
        use_container_width=True, height=420,
    )
    csv = df[cols].to_csv(index=False).encode("utf-8")
    st.download_button("DESCARGAR CSV", csv, "covid_veracruz_filtrado.csv", "text/csv")


# ============================================================
# PIE
# ============================================================
st.markdown(f"""
<div class="colophon">
    <div>OBSERVATORIO COVID-19 · VERACRUZ</div>
    <div>FUENTE · DGE / SSA · DATOS ABIERTOS</div>
    <div>PYTHON · SQLITE · STREAMLIT · PLOTLY</div>
</div>
""", unsafe_allow_html=True)
