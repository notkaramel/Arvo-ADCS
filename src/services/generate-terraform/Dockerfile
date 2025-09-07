FROM python:latest

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8080
# gunicorn -w 2 -b 0.0.0.0:8080 --timeout 120 terraform_app:app
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "--timeout", "360", "app:app"]