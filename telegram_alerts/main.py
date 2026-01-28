import time
import requests
from config import BOT_TOKEN, CANAL_ID, BARRIER_API_URL, CHECK_INTERVAL, PARAMETROS, API_KEY

# Headers para autenticación M2M
AUTH_HEADERS = {"X-API-Key": API_KEY}




def obtener_alertas():
    """Obtiene alertas pendientes desde la API."""
    try:
        response = requests.get(
            f"{BARRIER_API_URL}/api/alertas",
            headers=AUTH_HEADERS,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("alertas", [])
    except requests.RequestException as e:
        print(f"Error al consultar alertas: {e}")
        return []


def enviar_telegram(mensaje):
    """Envía mensaje al canal de Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": CANAL_ID,
            "text": mensaje,
            "parse_mode": "Markdown"
        }, timeout=30)
        return response.ok
    except requests.RequestException as e:
        print(f"Error enviando a Telegram: {e}")
        return False


def registrar_envio(alertas_enviadas):
    """Registra las alertas enviadas en la API."""
    if not alertas_enviadas:
        return
    try:
        requests.post(
            f"{BARRIER_API_URL}/api/alertas/registrar-envio",
            headers=AUTH_HEADERS,
            json=alertas_enviadas,
            timeout=30
        )
    except requests.RequestException as e:
        print(f"Error registrando envío: {e}")


def procesar_alertas():
    """Procesa y envía las alertas pendientes."""
    alertas = obtener_alertas()
    if not alertas:
        return 0

    print(f"Procesando {len(alertas)} alertas...")
    alertas_enviadas = []

    for alerta in alertas:
        for param_key, param_nombre, unidad in PARAMETROS:
            if not alerta.get(f"alerta_{param_key}"):
                continue

            valor = alerta.get(f"valor_{param_key}")
            limite = alerta.get(f"limite_{param_key}")
            if valor is None or limite is None:
                continue

            mensaje = (
                f"🚨 *ALERTA CONTAMINACIÓN*\n\n"
                f"📍 *Estación:* {alerta.get('nombre_estacion')}\n"
                f"⚠️ *Parámetro:* {param_nombre}\n"
                f"📊 *Valor:* {valor:.2f} {unidad} (límite: {limite:.2f})"
            )

            if enviar_telegram(mensaje):
                alertas_enviadas.append({
                    "id_estacion": alerta["id_estacion"],
                    "fecha_hora_alerta": alerta["fecha_hora_alerta"],
                    "nombre_estacion": alerta.get("nombre_estacion"),
                    "ciudad": alerta.get("ciudad"),
                    "parametro": param_key,
                    "valor": valor,
                    "limite": limite
                })
                print(f"  Enviada: {alerta.get('nombre_estacion')} - {param_nombre}")

            time.sleep(1)  # Pausa entre mensajes

    registrar_envio(alertas_enviadas)
    return len(alertas_enviadas)


def main():
    print("=" * 50)
    print("SERVICIO DE ALERTAS TELEGRAM")
    print(f"API: {BARRIER_API_URL}")
    print(f"Intervalo: {CHECK_INTERVAL // 60} minutos")
    print("=" * 50)

    while True:
        enviadas = procesar_alertas()
        if enviadas:
            print(f"Enviadas {enviadas} alertas")
        else:
            print("Sin alertas pendientes")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    time.sleep(30)  # Esperar a que el backend esté listo
    main()
