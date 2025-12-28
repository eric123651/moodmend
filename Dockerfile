FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY init_secure_db.py .

# Set environment variables
ENV PYTHONPATH=/app/src/backend
ENV FLASK_APP=src/backend/moodmend_backend.py

# Initialize database (optional, can be done in entrypoint)
# RUN python init_secure_db.py

# Set working directory to backend for runtime
WORKDIR /app/src/backend

# Expose port
EXPOSE 3000

# Run the application with Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-3000} --workers 4 --access-logfile - --error-logfile - moodmend_backend:app"]
