"""
Script para generar API keys seguras para los servicios M2M.

Ejecutar UNA VEZ antes de desplegar el proyecto:
    python scripts/generate_api_keys.py

Luego copiar las keys generadas al archivo .env
"""

import secrets

# Servicios que necesitan autenticarse con la API
SERVICES = [
    "ingestion-valencia",
    "telegram-alerts",
    "frontend",
]


def generate_api_key() -> str:
    """Genera una API key segura de 256 bits."""
    return secrets.token_urlsafe(32)


def main():
    print("\n" + "=" * 60)
    print("  GENERADOR DE API KEYS - Air Quality Project")
    print("=" * 60)

    print("\nGenerando API keys para los servicios...\n")

    keys = {}
    for service in SERVICES:
        keys[service] = generate_api_key()

    # Mostrar las keys generadas
    print("-" * 60)
    print("API KEYS GENERADAS:")
    print("-" * 60)
    for service, key in keys.items():
        print(f"\n  {service}:")
        print(f"    {key}")

    # Mostrar formato para .env
    print("\n" + "=" * 60)
    print("  COPIAR AL ARCHIVO .env:")
    print("=" * 60 + "\n")

    print("# API Keys para autenticación M2M (Machine-to-Machine)")
    for service, key in keys.items():
        env_var = service.upper().replace("-", "_") + "_API_KEY"
        print(f"{env_var}={key}")

    print("\n" + "=" * 60)
    print("  IMPORTANTE:")
    print("=" * 60)
    print("""
  1. Copia las líneas anteriores a tu archivo .env
  2. El archivo .env debe estar en .gitignore (NO subir al repo)
  3. Estas keys se insertarán automáticamente en la BD al arrancar
    """)


if __name__ == "__main__":
    main()
