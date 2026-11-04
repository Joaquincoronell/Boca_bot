FROM mcr.microsoft.com/playwright/python:v1.56.0-noble
WORKDIR /srv
COPY server/requirements.txt /srv/requirements.txt
RUN pip install --no-cache-dir -r /srv/requirements.txt
COPY server/app.py /srv/app.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 BOCA_DATA_DIR=/data
RUN mkdir -p /data
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
