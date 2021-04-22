FROM python:3.7

COPY backend/ /app/

WORKDIR /app
RUN mkdir -p /data
SHELL ["/bin/bash", "--login", "-c"]

CMD ["uvicorn", "backend.src.app:app", "--host", "0.0.0.0", "--port", "9500"]