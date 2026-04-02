FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt aiohttp

# Backend modules
COPY backend/ .

# Frontend static files
COPY frontend/ ./static/

EXPOSE 8080
EXPOSE 8765

CMD ["python", "entrypoint.py"]
