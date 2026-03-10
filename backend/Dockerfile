FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Use empty template so no personal data is baked into the image
COPY profile.json.template ./profile.json
COPY resume_parser.py .
COPY encryption_service.py .
COPY __init__.py .
COPY api ./api

EXPOSE 8000

CMD ["uvicorn", "resume_parser:app", "--host", "0.0.0.0", "--port", "8000"]

