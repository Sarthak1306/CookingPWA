# --- frontend build ---
FROM node:22-slim AS frontend
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- runtime ---
FROM python:3.12-slim
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY migrations/ ./migrations/
COPY --from=frontend /web/dist/ ./web/dist/

ENV KITCHEN_STATIC_DIR=web/dist
EXPOSE 8420

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8420"]
