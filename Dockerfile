FROM python:3.11-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir /app

EXPOSE 8765

CMD ["sh", "-c", "dreamloop init && dreamloop demo --if-empty --language ${DREAMLOOP_DEMO_LANGUAGE:-en} && dreamloop web --host 0.0.0.0 --port 8765"]
