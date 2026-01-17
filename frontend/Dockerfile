FROM python:3.11-slim

# Evitar archivos .pyc y logs en buffer
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copiar e instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY . .

# Exponer el puerto de Dash
EXPOSE 8050

# Ejecutar la app
# debug=False para producción, host 0.0.0.0 para que Docker lo vea
CMD ["python", "app.py"]