FROM python:3.11-slim

WORKDIR /app

COPY . .

EXPOSE 8080

ENV PORT=8080
ENV BACKEND_URL=http://backend:8000

CMD ["python", "dev_server.py"]
