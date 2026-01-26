import os #para leer las variables de entorno
import requests #para llamar a la API (los GETs)
import pandas as pd # para transformar el JSON en tabla y hacer cálculos

import dash #el freamework web (servidor+callbacks)
from dash import dcc, html, Input, Output, no_update 
import plotly.express as px  
from requests.exceptions import HTTPError
import plotly.graph_objects as go
import math



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
}



VALOR_LÍMITE = {
    "PM2.5": 15,
    "PM10": 45,
    "NO2": 25,
    "O3": 100,
    "SO2": 40,
}

TIME_OPTIONS = [
    {"label": "Ahora", "value": "Ahora"},
    {"label": "Últimas 8 horas", "value": "8h"},
    {"label": "Últimas 24 horas", "value": "24h"},
    {"label": "Última semana", "value": "7d"},
]

def level_for_pollutant(pollutant: str, value):
    if value is None:
        return ("⚪ Sin datos", "#95a5a6")

    limite = VALOR_LÍMITE.get(pollutant)
    if limite is None:
        return ("⚪ Sin umbral", "#95a5a6")

    tol = 1e-6

    if value < limite - tol:
        return ("🟢 Por debajo del límite", "#34a853")
    elif abs(value - limite) <= tol:
        return ("🟠 En el límite", "#fbbc05")
    else:
        return ("🔴 Límite superado", "#ea4335")



def severity_style(nivel: int):
    if nivel is None or nivel == 0:
        return ("#95a5a6", "⚪ Sin datos")
    
    if nivel == 1:
        return ("#ea4335", "🔴 Mala calidad del aire")

    if nivel == 2:
        return ("#ea4335", "🔴 Mala calidad del aire")

    if nivel == 3:
        return ("#ea4335", "🔴 Mala calidad del aire")

    if nivel == 4:
        return ("#ea4335", "🔴 Mala calidad del aire")

    return ("#7f8c8d", "⚪ Sin datos")

def fetch_alert_now(station_id: int):
    r = requests.get(
        f"{API_URL}/api/v1/alerts/now",
        params={"station_id": int(station_id)},
        timeout=10
    )
    if r.status_code == 404:
        return None  # no hay alerta
    r.raise_for_status()
    return r.json()



#mapa
def circle_polygon(lat, lon, radius_m=1000, n_points=60):
    R = 6378137  # radio de la Tierra (metros)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    lats, lons = [], []

    for i in range(n_points + 1):
        ang = 2 * math.pi * i / n_points
        d_lat = (radius_m / R) * math.cos(ang)
        d_lon = (radius_m / (R * math.cos(lat_rad))) * math.sin(ang)

        lats.append(math.degrees(lat_rad + d_lat))
        lons.append(math.degrees(lon_rad + d_lon))

    return lats, lons

def severity_fill(nivel):
    if nivel is None or pd.isna(nivel):
        return "rgba(149,165,166,0.25)"  # gris
    nivel = float(nivel)
    if nivel <= 1:
        return "rgba(52,168,83,0.30)"   # verde
    if nivel == 2:
        return "rgba(251,188,5,0.35)"   # amarillo
    return "rgba(234,67,53,0.40)"       # rojo



#zoom mapa
def choose_zoom(window: str) -> float:
    return {"Ahora": 15.5, "8h": 15.0, "24h": 14.5, "7d": 14.0}.get(window, 14.5)



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
#fetch del mapa
def fetch_station_history(station_id: int, window: str) -> pd.DataFrame:
    r = requests.get(
        f"{API_URL}/air_quality/history",
        params={"station_id": int(station_id), "window": window},
        timeout=15,
    )
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df

#Bloques 

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
        html.H4("Contaminantes en tu zona", style={"margin": "0 0 8px 0"}),
        html.Div(id="pollutants-subtitle", style={"fontSize": "12px", "opacity": "0.75", "marginBottom": "8px"}),
        dcc.Graph(id="pollutants-bar", style={"height": "360px"}),
        
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
            clearable=False,
        ),
        html.Div(id="alert-banner", style={"marginTop": "12px"}),

        dcc.RadioItems(
            id="time-range",
            options=TIME_OPTIONS,
            value="now",
            inline=True,
            style={"marginTop": "10px"},
        ),
   
        dcc.Graph(
            id="map-graph",
            style={"height": "520px", "marginTop": "15px"},
        ),



        html.Div(
            id="cards",
            style={"display": "flex", "gap": "12px", "marginTop": "12px"},
        ),

        pollutants_block,

        html.Div(id="status", style={"marginTop": "12px", "opacity": "0.8"}),

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
                    "backgroundColor": "#34a853",
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
            style={"backgroundColor": color, "color": "white", "padding": "14px", "borderRadius": "8px"},
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
            showlegend=False,
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
                marker=dict( symbol="circle", size=10, color="#000000"),
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


#callback mapa
@app.callback(
    Output("map-graph", "figure"),
    Input("dd-station", "value"),
    Input("time-range", "value"),
)
def update_map(station_id, window):
    if not station_id:
        return no_update

    df = fetch_station_history(int(station_id), window)
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return go.Figure()

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    row = df.sort_values("timestamp").iloc[-1]

    lat = float(row["lat"])
    lon = float(row["lon"])

    # Color del círculo basado en ALERTA ACTIVA (igual que el banner)
    alert = fetch_alert_now(int(station_id))

    if alert is None:
        fill_color = "rgba(52,168,83,0.30)"   # verde
        hover_txt = "Sin alerta activa"
    else:
        fill_color = "rgba(234,67,53,0.40)"   # rojo
        hover_txt = f"ALERTA · Severidad: {alert.get('nivel_severidad')}"

    radius = {"now": 700, "8h": 1000, "24h": 1300, "7d": 1700}.get(window, 1000)
    poly_lat, poly_lon = circle_polygon(lat, lon, radius_m=radius)

    fig = go.Figure()

    fig.add_trace(
        go.Scattermapbox(
            lat=poly_lat,
            lon=poly_lon,
            fill="toself",
            fillcolor=fill_color,
            line=dict(color="rgba(0,0,0,0.4)", width=2),
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scattermapbox(
            lat=[lat],
            lon=[lon],
            mode="markers",
            marker=dict(size=8, color="black"),
            hovertext=hover_txt,
            hoverinfo="text",
        )
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center={"lat": lat, "lon": lon},
        mapbox_zoom=choose_zoom(window),
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"Estación {station_id} | Ventana: {window}",
        showlegend=False,
    )

    return fig



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)