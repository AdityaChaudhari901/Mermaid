FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY serverless_handler.py .

# Expose port for local testing
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# For Boltic Serverless / Google Cloud Functions
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "60", "--workers", "4", "app:app"]
