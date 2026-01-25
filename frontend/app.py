import os #para leer las variables de entorno
import requests #para llamar a la API (los GETs)
import pandas as pd # para transformar el JSON en tabla y hacer cálculos

import dash #el freamework web (servidor+callbacks)
from dash import dcc, html, Input, Output
import plotly.express as px  # (no lo usamos aún, pero viene bien tenerlo para el heatmap)

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


# ---------- Layout ---------- estructura de la página

app.layout = html.Div(
    style={"fontFamily": "Arial", "maxWidth": "900px", "margin": "0 auto", "padding": "20px"},
    children=[
        html.H2("🌤️ Selecciona tu estación"),

        dcc.Dropdown( #crea el desplegable
            id="dd-station", #para referenciar en callbacks
            placeholder="Cargando estaciones...",
            clearable=False #evita que usuario lo deje vacío
        ),

        html.Div(id="alert-banner", style={"marginTop": "12px"}),

        html.Div(
            id="cards",
            style={"display": "flex", "gap": "12px", "marginTop": "12px"}
        ),

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)