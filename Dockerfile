FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY profile.json .
COPY resume_parser_microservice.py .

EXPOSE 8000

CMD ["uvicorn", "resume_parser_microservice:app", "--host", "0.0.0.0", "--port", "8000"]

