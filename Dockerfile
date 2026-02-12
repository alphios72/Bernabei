# Stage 1: Build Frontend
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend ./
RUN npm run build

# Stage 2: Build Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend .

# Copy frontend build to static folder (served by FastAPI)
COPY --from=frontend-build /app/frontend/dist /app/static

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
