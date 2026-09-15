# ---------- Frontend build ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# ---------- Runtime ----------
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY --from=frontend /build/dist ./frontend/dist

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["python", "-m", "backend.main"]
