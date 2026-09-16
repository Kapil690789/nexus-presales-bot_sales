FROM node:20-bookworm-slim AS widget
WORKDIR /widget
COPY widget/package.json ./
RUN npm install
COPY widget/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app PORT=8080
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY config ./config
COPY backend ./backend
COPY public ./public
COPY --from=widget /widget/dist ./widget/dist
EXPOSE 8080
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
