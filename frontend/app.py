import requests #para llamar a la API (los GETs)
import pandas as pd # para transformar el JSON en tabla y hacer cálculos

import dash #el freamework web (servidor+callbacks)
from dash import dcc, html, Input, Output, no_update 
import plotly.express as px  
from requests.exceptions import HTTPError
import plotly.graph_objects as go
import math
from config import BARRIER_API_URL, FRONTEND_API_KEY





app = dash.Dash(__name__, title="🌤️ App Ciudadana | Calidad del aire") #Creamos la app "Dash" y título del navegador

# CSS personalizado para tooltips
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .podio-card {
                position: relative;
            }
            .podio-card .tooltip-content {
                visibility: hidden;
                opacity: 0;
                position: absolute;
                bottom: 105%;
                left: 50%;
                transform: translateX(-50%);
                background-color: #1a202c;
                color: white;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 11px;
                white-space: pre-line;
                z-index: 1000;
                min-width: 160px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: opacity 0.2s, visibility 0.2s;
                text-align: left;
                line-height: 1.5;
            }
            .podio-card .tooltip-content::after {
                content: "";
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -6px;
                border-width: 6px;
                border-style: solid;
                border-color: #1a202c transparent transparent transparent;
            }
            .podio-card:hover .tooltip-content {
                visibility: visible;
                opacity: 1;
            }
            .podio-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


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


#este helper nos sirve para comparar la medida actual con el "límite recomendado"
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
#centraliza el criterio, si cambiamos esto afecta a todos los gráficos.
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
        f"{BARRIER_API_URL}/api/alerts/now",
        params={"station_id": int(station_id)},
        headers={"X-API-Key": FRONTEND_API_KEY},
        timeout=10
    )
    if r.status_code == 404:
        return None  # no hay alerta
    r.raise_for_status() #si backend devuelve 400/500 salta un error
    return r.json() #convierte la respuesta JSON en dict/list de Python

#tarjeta ranking estaciones con menor contaminación
def menos_contaminacion(limit: int = 3) -> dict:
    r = requests.get(f"{BARRIER_API_URL}/api/zonas-verdes", params={"limit": limit}, headers={"X-API-Key": FRONTEND_API_KEY}, timeout=20)
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
    return {"Ahora": 12.5, "8h": 12.5, "24h": 12.5, "7d": 12.5}.get(window, 12.5)



def fetch_hourly(limit=5000) -> pd.DataFrame:
    r = requests.get(f"{BARRIER_API_URL}/api/hourly-metrics", params={"limit": limit}, headers={"X-API-Key": FRONTEND_API_KEY}, timeout=20)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def fetch_history(station_id: int, days: int, metric: str) -> pd.DataFrame:
    r = requests.get(
        f"{BARRIER_API_URL}/api/history/hourly",
        params={"station_id": station_id, "days": days, "metric": metric},
        headers={"X-API-Key": FRONTEND_API_KEY},
        timeout=20
    )
    r.raise_for_status()
    return pd.DataFrame(r.json())

def fetch_station_latest_hourly(station_id: int) -> dict:
    url = f"{BARRIER_API_URL}/api/station/latest-hourly"
    r = requests.get(url, params={"station_id": station_id}, headers={"X-API-Key": FRONTEND_API_KEY}, timeout=10)
    r.raise_for_status()
    return r.json()

#fetch del mapa
def fetch_station_history(station_id: int, window: str) -> pd.DataFrame:
    r = requests.get(
        f"{BARRIER_API_URL}/air_quality/history",
        params={"station_id": int(station_id), "window": window},
        headers={"X-API-Key": FRONTEND_API_KEY},
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
        "width": "420px",
        "height": "300px",
        "padding": "20px",
        "borderRadius": "10px",
        "border": "1px solid #e5e7eb",
        "backgroundColor": "white",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.06)",
        "boxSizing": "border-box",
    },
    children=[
        html.H4("Contaminantes en tu zona", style={"margin": "0 0 4px 0", "fontSize": "14px"}),
        html.Div(id="pollutants-subtitle", style={"fontSize": "11px", "opacity": "0.75", "marginBottom": "4px"}),
        dcc.Graph(id="pollutants-bar", style={"height": "230px"}),
    ],
)

#                       --LAYOUT-- estructura de la página --
app.layout = html.Div(
    style={"fontFamily": "Arial", "maxWidth": "900px", "margin": "0 auto", "padding": "20px"},
    children=[
        html.H2("Selecciona tu estación"),

        # Fila: Dropdown + Banner (izquierda) | Ranking (derecha, alineado con tarjeta contaminantes)
        html.Div(
            style={"display": "flex", "alignItems": "flex-start", "gap": "20px"},
            children=[ # "Children": lo que “contiene” un componente
                # Columna izquierda - Dropdown y Banner (mismo ancho que mapa: 450px)
                html.Div(
                    style={"width": "450px", "flexShrink": "0"},
                    children=[
                        dcc.Dropdown( #desplegable
                            id="dd-station",
                            placeholder="Cargando estaciones...",
                            clearable=False,
                            style={"width": "100%", "maxWidth": "400px"},
                        ),
                        html.Div(id="alert-banner", style={"marginTop": "12px", "maxWidth": "400px"}),
                    ],
                ),
                # Columna derecha - Ranking zonas verdes (mismo ancho que tarjeta contaminantes)
                html.Div(
                    style={
                        "width": "420px",
                        "flexShrink": "0",
                        "backgroundColor": "#f0fdf4",
                        "borderRadius": "15px",
                        "padding": "20px",
                        "border": "1px solid #dcfce7",
                        "boxShadow": "0 4px 12px rgba(0,0,0,0.05)",
                        "boxSizing": "border-box",
                    },
                    children=[
                        html.H4("Ranking mejores zonas", style={"margin": "0 0 4px 0", "color": "#166534", "fontSize": "16px", "fontWeight": "700"}),
                        html.P("Aire más puro ahora mismo", style={"margin": "0 0 15px 0", "fontSize": "12px", "color": "#15803d"}),
                        html.Div(id="zonas-verdes-list"),
                    ]
                ),
            ],
        ),

        # Fila: Mapa (izquierda) + Gráfico contaminantes (derecha)
        html.Div(
            style={"display": "flex", "gap": "20px", "marginTop": "15px"},
            children=[
                # Mapa + selector de tiempo
                html.Div(
                    children=[
                        dcc.Graph(
                            id="map-graph",
                            style={"height": "300px", "width": "450px"},
                        ),
                        dcc.RadioItems(
                            id="time-range",
                            options=TIME_OPTIONS,
                            value="now",
                            inline=True,
                            style={"marginTop": "8px", "fontSize": "12px"},
                        ),
                    ],
                ),
                pollutants_block,
            ],
        ),

        html.Div(
            id="cards",
            style={"display": "flex", "gap": "12px", "marginTop": "12px", "width":"70%"},
        ),

        html.Div(id="status", style={"marginTop": "12px", "opacity": "0.8"}),

        dcc.Store(id="init", data=True),
    ]
)



# ---------- Callbacks ----------
#callback estaciones
@app.callback(
    Output("dd-station", "options"), #lista de estaciones renderizada en UI
    Output("dd-station", "value"), #estación seleccionada por defecto
    Input("init", "data"),
)
def load_stations(_):
    try:
        r = requests.get(f"{BARRIER_API_URL}/api/stations", headers={"X-API-Key": FRONTEND_API_KEY}, timeout=10)
        r.raise_for_status()
        stations = r.json()

        options = [
            {"label": s["nombre_estacion"], "value": s["id_estacion"]}
            for s in stations
        ]

        # Seleccionar la primera estación por defecto si hay opciones
        default_value = options[0]["value"] if options else None
        return options, default_value
    except Exception as e:
        print(f"Error cargando estaciones: {e}")
        return [], None


@app.callback(
    Output("zonas-verdes-list", "children"),
    Input("init", "data"),
)
def load_zonas_verdes(_):
    try:
        data = menos_contaminacion(limit=3)
        if not data:
            return html.Div("No hay datos disponibles", style={"opacity": "0.7", "fontSize": "12px"})

        medallas = {1: "🥇", 2: "🥈", 3: "🥉"}

        # Configuración del podio: tamaño y altura para cada posición
        podio_config = {
            1: {"height": "100px", "fontSize": "28px", "nameFontSize": "13px", "marginTop": "0px"},
            2: {"height": "85px", "fontSize": "22px", "nameFontSize": "12px", "marginTop": "15px"},
            3: {"height": "75px", "fontSize": "20px", "nameFontSize": "11px", "marginTop": "25px"},
        }

        def formato_valor(val):
            """Formatea el valor del contaminante para el tooltip"""
            if val is None:
                return "N/D"
            return f"{val:.1f}"

        def crear_tooltip(zona):
            """Crea el texto del tooltip con los niveles de contaminantes"""
            lineas = [f"📍 {zona.get('nombre_estacion', 'Estación')}"]
            lineas.append("─" * 20)
            lineas.append(f"NO₂:   {formato_valor(zona.get('promedio_no2'))} µg/m³")
            lineas.append(f"PM2.5: {formato_valor(zona.get('promedio_pm25'))} µg/m³")
            lineas.append(f"PM10:  {formato_valor(zona.get('promedio_pm10'))} µg/m³")
            lineas.append(f"O₃:    {formato_valor(zona.get('promedio_ozono'))} µg/m³")
            lineas.append(f"SO₂:   {formato_valor(zona.get('promedio_so2'))} µg/m³")
            return "\n".join(lineas)

        def crear_podio_card(posicion, zona):
            nombre = zona.get("nombre_estacion", "Estación desconocida")
            config = podio_config[posicion]
            tooltip_text = crear_tooltip(zona)

            return html.Div(
                className="podio-card",
                style={
                    "backgroundColor": "white",
                    "padding": "10px",
                    "borderRadius": "10px",
                    "border": "1px solid #f0f0f0",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.05)",
                    "textAlign": "center",
                    "height": config["height"],
                    "display": "flex",
                    "flexDirection": "column",
                    "justifyContent": "center",
                    "alignItems": "center",
                    "marginTop": config["marginTop"],
                    "flex": "1",
                    "cursor": "pointer",
                    "transition": "transform 0.2s, box-shadow 0.2s",
                },
                children=[
                    # Tooltip que aparece al hacer hover
                    html.Div(tooltip_text, className="tooltip-content"),
                    html.Span(medallas.get(posicion, "📍"), style={"fontSize": config["fontSize"]}),
                    html.Div(
                        nombre,
                        style={
                            "fontWeight": "700",
                            "fontSize": config["nameFontSize"],
                            "color": "#1a202c",
                            "marginTop": "6px",
                            "lineHeight": "1.2",
                            "overflow": "hidden",
                            "textOverflow": "ellipsis",
                            "maxWidth": "120px",
                        }
                    ),
                ]
            )

        # Crear las cards para cada posición (si existen)
        cards = {}
        for i, zona in enumerate(data, 1):
            if i <= 3:
                cards[i] = crear_podio_card(i, zona)

        # Orden del podio: 2º | 1º | 3º
        podio_items = []
        if 2 in cards:
            podio_items.append(cards[2])
        if 1 in cards:
            podio_items.append(cards[1])
        if 3 in cards:
            podio_items.append(cards[3])

        return html.Div(
            style={
                "display": "flex",
                "alignItems": "flex-end",
                "justifyContent": "center",
                "gap": "12px",
            },
            children=podio_items
        )
    except Exception as e:
        return html.Div(f"Error: {e}", style={"color": "red", "fontSize": "12px"})

#CALLBACK DEL BANNER DE ALERTA POR ZONA
@app.callback(
    Output("alert-banner", "children"),
    Input("dd-station", "value"),
)
def render_banner(station_id):
    if station_id is None:
        return html.Div("Selecciona una estación.", style={"opacity": "0.7"})

    try:
        r = requests.get(
            f"{BARRIER_API_URL}/api/alerts/now",
            params={"station_id": int(station_id)},
            headers={"X-API-Key": FRONTEND_API_KEY},
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
        ts = data.get("fecha_hora_alerta", "")

        why = WHY_MAP.get(contaminante, "Puede afectar a la salud respiratoria.")

        return html.Div(
            style={"backgroundColor": color, "color": "white", "padding": "14px", "borderRadius": "8px"},
            children=[
                html.H3(f"{title} · {station_name}", style={"margin": "0 0 6px 0"}),
                html.Div(f"Contaminante principal: {contaminante}", style={"marginTop": "8px", "fontWeight": "700"}),
                html.Div(why, style={"marginTop": "4px", "opacity": "0.95"}),
                html.Div(f"Última actualización: {ts}", style={"marginTop": "10px", "fontSize": "12px", "opacity": "0.85"}),
            ],
        )

    except HTTPError as e:
        # errores 4xx/5xx (distintos de 404)
        return html.Div(f"❌ Error cargando alerta: {e}", style={"color": "red"})

    except Exception as e:
        return html.Div(f"❌ Error inesperado: {e}", style={"color": "red"})

#CALLBACK GRÁFICO BARRAS - CONTAMINANTE 
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

    station_name = data.get("nombre_estacion", f"Estación {station_id}")
    measure_hour = data.get("fecha_hora", "")

    pollutants = [
        ("PM2.5", data.get("promedio_pm25")),
        ("PM10",  data.get("promedio_pm10")),
        ("NO2",   data.get("promedio_no2")),
        ("O3",    data.get("promedio_ozono")),
        ("SO2",   data.get("promedio_so2")),
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

    # --- Marca del límite ---
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
        go.Scattermap(
            lat=poly_lat,
            lon=poly_lon,
            fill="toself",
            fillcolor=fill_color,
            line=dict(color="rgba(0,0,0,0.4)", width=2),
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scattermap(
            lat=[lat],
            lon=[lon],
            mode="markers",
            marker=dict(size=8, color="black"),
            hovertext=hover_txt,
            hoverinfo="text",
        )
    )

    fig.update_layout(
        map_style="open-street-map",
        map_center={"lat": lat, "lon": lon},
        map_zoom=choose_zoom(window),
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"Estación {station_id} | Ventana: {window}",
        showlegend=False,
    )

    return fig



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)