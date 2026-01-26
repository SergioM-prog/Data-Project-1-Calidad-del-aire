import os #para leer las variables de entorno
import requests #para llamar a la API (los GETs)
import pandas as pd # para transformar el JSON en tabla y hacer cálculos

import dash #el freamework web (servidor+callbacks)
from dash import dcc, html, Input, Output
import plotly.express as px  
from requests.exceptions import HTTPError


API_URL = os.getenv("API_URL", "http://backend:8000") #lee la variable API_URL

app = dash.Dash(__name__, title="🌤️ App Ciudadana | Calidad del aire") #Creamos la app "Dash" y título del navegador


# ---------- Helpers ----------

def card(title: str, value: str, subtitle: str = ""):
    return html.Div(
        style={
            "flex": "1",
            "padding": "12px",
            "borderRadius": "10px",
            "border": "1px solid #e5e7eb",
            "backgroundColor": "white",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.06)",
        },
        children=[
            html.Div(title, style={"fontWeight": "700", "marginBottom": "6px"}),
            html.Div(value, style={"fontSize": "18px", "fontWeight": "700"}),
            html.Div(subtitle, style={"marginTop": "6px", "opacity": "0.8", "fontSize": "13px"}) if subtitle else None,
        ],
    )


WHY_MAP = {
    "NO2": "Suele estar relacionado con el tráfico y puede irritar las vías respiratorias.",
    "PM25": "Partículas muy finas que pueden afectar a la respiración, sobre todo en personas sensibles.",
    "PM2.5": "Partículas muy finas que pueden afectar a la respiración, sobre todo en personas sensibles.",
    "PM10": "Partículas en el aire que pueden empeorar alergias o molestias respiratorias.",
    "O3": "Ozono: puede aumentar con sol/calor y provocar tos o irritación.",
    "SO2": "Puede causar molestias respiratorias, sobre todo en personas sensibles.",
    "CO": "Relacionado con combustión; en niveles altos puede ser peligroso.",
}

THRESHOLDS = {
    "PM2.5": [(10, "🟢 Bueno", "#2ecc71"), (20, "🟡 Precaución", "#f1c40f"), (35, "🟠 Moderado", "#e67e22"), (9999, "🔴 Alto", "#e74c3c")],
    "PM10":  [(20, "🟢 Bueno", "#2ecc71"), (40, "🟡 Precaución", "#f1c40f"), (50, "🟠 Moderado", "#e67e22"), (9999, "🔴 Alto", "#e74c3c")],
    "NO2":   [(40, "🟢 Bueno", "#2ecc71"), (100, "🟡 Precaución", "#f1c40f"), (200, "🟠 Moderado", "#e67e22"), (9999, "🔴 Alto", "#e74c3c")],
    "O3":    [(60, "🟢 Bueno", "#2ecc71"), (120, "🟡 Precaución", "#f1c40f"), (180, "🟠 Moderado", "#e67e22"), (9999, "🔴 Alto", "#e74c3c")],
    "SO2":   [(100, "🟢 Bueno", "#2ecc71"), (200, "🟡 Precaución", "#f1c40f"), (350, "🟠 Moderado", "#e67e22"), (9999, "🔴 Alto", "#e74c3c")],
    "CO":    [(2, "🟢 Bueno", "#2ecc71"), (5, "🟡 Precaución", "#f1c40f"), (10, "🟠 Moderado", "#e67e22"), (9999, "🔴 Alto", "#e74c3c")],
}

VALOR_LÍMITE = {
    "PM2.5": 10,
    "PM10": 20,
    "NO2": 40,
    "O3": 60,
    "SO2": 100,
    "CO": 2,
}

def level_for_pollutant(pollutant: str, value):
    """Devuelve (label, color) según el contaminante y su valor."""
    if value is None:
        return ("⚪ Sin datos", "#95a5a6")
    rules = THRESHOLDS.get(pollutant)
    if not rules:
        return ("⚪ Sin umbral", "#95a5a6")
    for max_v, label, color in rules:
        if value <= max_v:
            return (label, color)
    return ("⚪", "#95a5a6")


def severity_style(nivel: int):
    if nivel is None or nivel == 0:
        return ("#95a5a6", "⚪ Sin datos")
    
    if nivel == 1:
        return ("#f1c40f", "🟡 Precaución")

    if nivel == 2:
        return ("#e67e22", "🟠 Moderado")

    if nivel == 3:
        return ("#e74c3c", "🔴 Aire malo")

    if nivel == 4:
        return ("#8e44ad", "🟣 Muy malo")

    return ("#7f8c8d", "⚪ Sin datos")



def fetch_hourly(limit=5000) -> pd.DataFrame:
    r = requests.get(f"{API_URL}/api/v1/hourly-metrics", params={"limit": limit}, timeout=20)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def fetch_history(station_id: int, days: int, metric: str) -> pd.DataFrame:
    r = requests.get(
        f"{API_URL}/api/v1/history/hourly",
        params={"station_id": station_id, "days": days, "metric": metric},
        timeout=20
    )
    r.raise_for_status()
    return pd.DataFrame(r.json())

def fetch_station_latest_hourly(station_id: int) -> dict:
    url = f"{API_URL}/api/v1/station/latest-hourly"
    r = requests.get(url, params={"station_id": station_id}, timeout=10)
    r.raise_for_status()
    return r.json()

#Bloques 
pollutant_help = html.Div(
    style={"marginTop": "10px", "fontSize": "13px", "opacity": "0.9", "lineHeight": "1.35"},
    children=[
        html.Ul(
            style={"margin": "8px 0 0 18px"},
            children=[
                html.Li([html.B("PM2.5:"), " partículas muy pequeñas que pueden llegar a los pulmones."]),
                html.Li([html.B("PM10:"),  " polvo, polen u otras partículas del aire que pueden causar molestias respiratorias."]),
                html.Li([html.B("NO2:"),   " gas asociado al tráfico; irrita vías respiratorias."]),
                html.Li([html.B("O3:"),    " ozono a nivel del suelo; puede causar irritación."]),
                html.Li([html.B("SO2:"),   " gas procedente de procesos industriales; puede causar molestias respiratorias."]),
                html.Li([html.B("CO:"),    " monóxido de carbono, generado por combustión incompleta (vehículos, calefacciones)."]),
            ],
        )
    ],
)

pollutants_block = html.Div(
    style={
        "marginTop": "16px",
        "padding": "12px",
        "borderRadius": "10px",
        "border": "1px solid #e5e7eb",
        "backgroundColor": "white",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.06)",
    },
    children=[
        html.H4("Contaminantes (última medición)", style={"margin": "0 0 8px 0"}),
        html.Div(id="pollutants-subtitle", style={"fontSize": "12px", "opacity": "0.75", "marginBottom": "8px"}),
        dcc.Graph(id="pollutants-bar", style={"height": "360px"}),
        html.Div(
            "🔴 El punto rojo indica el límite recomendado para reducir riesgos a la salud. "
            "Superarlo no implica una alerta, pero se recomienda precaución.",
            style={
                "fontSize": "13px",
                "opacity": "0.8",
                "marginTop": "6px",
                "marginBottom": "10px",
            },
        ),

        pollutant_help,
    ],
)



# ---------- Layout ---------- estructura de la página

app.layout = html.Div(
    style={"fontFamily": "Arial", "maxWidth": "900px", "margin": "0 auto", "padding": "20px"},
    children=[
        html.H2("🌤️ Selecciona tu estación"),

        dcc.Dropdown(
            id="dd-station",
            placeholder="Cargando estaciones...",
            clearable=False
        ),

        html.Div(id="alert-banner", style={"marginTop": "12px"}),

        html.Div(
            id="cards",
            style={"display": "flex", "gap": "12px", "marginTop": "12px"}
        ),

        pollutants_block,

        html.Div(id="status", style={"marginTop": "12px", "opacity": "0.8"}),
# dispara el callback de carga de estaciones 1 vez al cargar
        dcc.Store(id="init", data=True),
    ],
)



# ---------- Callbacks ----------

@app.callback(
    Output("dd-station", "options"),
    Output("dd-station", "value"),
    Output("status", "children"),
    Input("init", "data"),
)
def load_stations(_):
    try:
        response = requests.get(
            f"{API_URL}/api/v1/hourly-metrics",
            params={"limit": 5000},
            timeout=15
        )
        response.raise_for_status()

        df = pd.DataFrame(response.json())

        if "station_id" not in df.columns or "station_name" not in df.columns:
            return [], None, "❌ La API no devuelve station_id / station_name"

        stations = (
            df[["station_id", "station_name"]]
            .dropna()
            .drop_duplicates()
            .sort_values("station_name")
        )

        options = [
            {"label": row["station_name"], "value": int(row["station_id"])}
            for _, row in stations.iterrows()
        ]

        default_value = options[0]["value"] if options else None

        return options, default_value, None 

    except Exception as e:
        return [], None, f"❌ Error cargando estaciones: {e}"



@app.callback(
    Output("alert-banner", "children"),
    Input("dd-station", "value"),
)
def render_banner(station_id):
    if station_id is None:
        return html.Div("Selecciona una estación.", style={"opacity": "0.7"})

    try:
        r = requests.get(
            f"{API_URL}/api/v1/alerts/now",
            params={"station_id": int(station_id)},
            timeout=15
        )


        if r.status_code == 404:
            return html.Div(
                style={
                    "backgroundColor": "#2ecc71",
                    "color": "black",
                    "padding": "14px",
                    "borderRadius": "8px",
                },
                children=[
                    html.H3("✅ Sin alertas activas", style={"margin": "0 0 6px 0"}),
                    html.Div(
                        "No se detectan niveles nocivos en este momento en esta estación.",
                        style={"opacity": "0.95"},
                    ),
                ],
            )

       
        r.raise_for_status()
        data = r.json()

        nivel = int(data.get("nivel_severidad", 0))
        color, title = severity_style(nivel)

        station_name = data.get("nombre_estacion", f"Estación {station_id}")
        contaminante = data.get("contaminante_principal", "—")
        reco = data.get("recomendacion", "")
        ts = data.get("fecha_hora_alerta", "")

        why = WHY_MAP.get(contaminante, "Puede afectar a la salud respiratoria.")

        return html.Div(
            style={"backgroundColor": color, "color": "black", "padding": "14px", "borderRadius": "8px"},
            children=[
                html.H3(f"{title} · {station_name}", style={"margin": "0 0 6px 0"}),
                html.Div(f"Recomendación: {reco}", style={"marginTop": "8px", "fontWeight": "700"}),
                html.Div(f"Principal contaminante: {contaminante}", style={"marginTop": "10px"}),
                html.Div(why, style={"marginTop": "4px", "opacity": "0.95"}),
                html.Div(f"Última actualización: {ts}", style={"marginTop": "10px", "fontSize": "12px", "opacity": "0.85"}),
            ],
        )

    except HTTPError as e:
        # errores 4xx/5xx (distintos de 404)
        return html.Div(f"❌ Error cargando alerta: {e}", style={"color": "red"})

    except Exception as e:
        return html.Div(f"❌ Error inesperado: {e}", style={"color": "red"})
    
@app.callback(
    Output("pollutants-bar", "figure"),
    Output("pollutants-subtitle", "children"),
    Input("dd-station", "value"),
)
def update_pollutants_bar(station_id):
    import plotly.graph_objects as go
    import numpy as np

    # --- Figura base (por si hay errores) ---
    def empty_fig():
        fig = go.Figure()
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Concentración (µg/m³)",
            yaxis_title="",
        )
        return fig

    if not station_id:
        return empty_fig(), "Selecciona una estación para ver los contaminantes."

    data = fetch_station_latest_hourly(int(station_id))
    if not data:
        return empty_fig(), "No hay datos disponibles para esta estación."

    station_name = data.get("station_name", f"Estación {station_id}")
    measure_hour = data.get("measure_hour", "")

    pollutants = [
        ("PM2.5", data.get("avg_pm25")),
        ("PM10",  data.get("avg_pm10")),
        ("NO2",   data.get("avg_no2")),
        ("O3",    data.get("avg_o3")),
        ("SO2",   data.get("avg_so2")),
        ("CO",    data.get("avg_co")),
    ]

    # Creamos DF y SOLO quitamos filas sin valor actual
    df = pd.DataFrame(pollutants, columns=["pollutant", "value"])
    df = df[df["value"].notna()].copy()

    if df.empty:
        return empty_fig(), f"{station_name} · Última medición: {measure_hour} · Sin valores disponibles."

    # Orden fijo
    order = ["PM2.5", "PM10", "NO2", "O3", "SO2", "CO"]
    df["pollutant"] = pd.Categorical(df["pollutant"], categories=order, ordered=True)
    df = df.sort_values("pollutant")

    # --- Límite recomendado (NUMÉRICO si existe) ---
    # IMPORTANTE: el dict debe tener claves EXACTAS: "O3" (letra O, no cero)
    df["valor_limite"] = df["pollutant"].map(VALOR_LÍMITE)

    # --- Nivel y color ---
    df["level_label"] = df.apply(lambda r: level_for_pollutant(r["pollutant"], r["value"])[0], axis=1)
    df["color"] = df.apply(lambda r: level_for_pollutant(r["pollutant"], r["value"])[1], axis=1)

    # Si level_label viene None, lo arreglamos para el tooltip
    df["level_label"] = df["level_label"].fillna("Sin nivel")

    # Para tooltip: límite en texto ("N/D" si no hay)
    df["limite_txt"] = df["valor_limite"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "N/D")

    # --- Eje X: usa máximo entre valores actuales y límites que existan ---
    max_value = float(df["value"].max())

    # límites numéricos (puede que no existan para algún contaminante)
    limites_num = df["valor_limite"].dropna()
    if not limites_num.empty:
        max_lim = float(limites_num.max())
        max_x = max(max_value, max_lim) * 1.20
    else:
        max_x = max_value * 1.20

    fig = go.Figure()

    # --- Barras (valor actual) ---
    fig.add_trace(
        go.Bar(
            x=df["value"],
            y=df["pollutant"],
            orientation="h",
            marker=dict(color=df["color"]),
            # customdata: (limite_txt, level_label)
            customdata=list(zip(df["limite_txt"], df["level_label"])),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Nivel actual: %{x:.1f} µg/m³<br>"
                "Límite recomendado: %{customdata[0]} µg/m³<br>"
                "%{customdata[1]}"
                "<extra></extra>"
            ),
            name="Actual",
        )
    )

    # --- Marca del límite (solo para los que tienen límite numérico) ---
    df_lim = df[df["valor_limite"].notna()].copy()
    if not df_lim.empty:
        fig.add_trace(
            go.Scatter(
                x=df_lim["valor_limite"],
                y=df_lim["pollutant"],
                mode="markers",
                marker=dict( symbol="circle", size=10, color="#e74c3c"),
                hovertemplate="<b>%{y}</b><br>Límite recomendado: %{x:.0f} µg/m³<extra></extra>",
                name="Límite recomendado",
            )
        )

    fig.update_layout(
        margin=dict(l=10, r=20, t=10, b=10),
        xaxis=dict(title="Concentración (µg/m³)", range=[0, max_x]),
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    subtitle = f"{station_name} · Última medición: {measure_hour}"
    return fig, subtitle

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)