import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import requests
import os

# CONFIGURACIÓN
# Buscamos la variable de entorno API_URL. 
# Si no existe (ej. probando en local sin docker), intentamos localhost:8000
API_URL = os.getenv("API_URL", "http://backend:8000")

# Inicializar Dash
app = dash.Dash(_name_, title="Air Quality Citizen App")

# LAYOUT (Lo que ve el usuario)
app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'maxWidth': '1000px', 'margin': '0 auto', 'padding': '20px'}, children=[
    
    # 1. Encabezado
    html.H1("🌤️ Monitor Ciudadano de Calidad del Aire", style={'textAlign': 'center', 'color': '#2c3e50'}),
    html.P("Datos en tiempo real validados por la red municipal.", style={'textAlign': 'center', 'color': '#7f8c8d'}),

    # 2. Espacio reservado para ALERTAS (Se llena dinámicamente)
    html.Div(id='alert-banner', style={'margin': '20px 0'}),

    # 3. Gráfico Principal
    html.Div([
        dcc.Graph(id='live-graph'),
    ], style={'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)', 'borderRadius': '5px', 'padding': '10px'}),

    # 4. Componente invisible que actualiza la página cada 60 segundos
    dcc.Interval(
        id='interval-component',
        interval=60*1000, # 1 minuto en milisegundos
        n_intervals=0
    )
])

# CALLBACK (La lógica que se ejecuta cada minuto)
@app.callback(
    [Output('live-graph', 'figure'),
     Output('alert-banner', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    try:
        # A) PEDIR DATOS A LA API (Backend)
        # Endpoint que definimos en backend/main.py
        response = requests.get(f"{API_URL}/api/v1/hourly-metrics")
        
        if response.status_code != 200:
            return px.line(title="Error en API"), html.Div("API no disponible", style={'color': 'red'})

        data = response.json()
        df = pd.read_json(pd.io.json.json_normalize(data).to_json(orient='records'))

        if df.empty:
            return px.line(title="Esperando datos..."), None

        # B) LÓGICA DE ALERTA
        # Miramos el último dato registrado
        latest_record = df.iloc[0]
        latest_val = latest_record['avg_no2']
        
        alert_element = None
        
        # Umbral de ejemplo: 40 ug/m3
        if latest_val > 40:
            alert_element = html.Div([
                html.H3(f"⚠️ ALERTA: Nivel de NO2 Alto ({latest_val} µg/m³)", style={'margin': '0'}),
                html.P("Se recomienda limitar el ejercicio al aire libre.")
            ], style={'backgroundColor': '#e74c3c', 'color': 'white', 'padding': '15px', 'borderRadius': '5px', 'textAlign': 'center'})
        else:
             alert_element = html.Div([
                html.H3(f"✅ Calidad del Aire Buena ({latest_val} µg/m³)", style={'margin': '0'}),
            ], style={'backgroundColor': '#27ae60', 'color': 'white', 'padding': '15px', 'borderRadius': '5px', 'textAlign': 'center'})

        # C) GENERAR GRÁFICO
        fig = px.line(df, x='measure_hour', y='avg_no2', color='station_name', 
                      title='Evolución Horaria de NO2 por Estación',
                      labels={'measure_hour': 'Hora', 'avg_no2': 'NO2 (µg/m³)'})
        
        return fig, alert_element

    except Exception as e:
        print(f"Error en frontend: {e}")
        return px.line(title="Error de conexión"), None

if _name_ == '_main_':
    # host 0.0.0.0 es necesario para Docker
    app.run_server(host='0.0.0.0', port=8050, debug=False)