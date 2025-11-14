FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download Spleeter models during build (optional but recommended)
RUN python -c "from spleeter.separator import Separator; Separator('spleeter:2stems')"

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Run with gunicorn for production
CMD ["python", "app.py"]
