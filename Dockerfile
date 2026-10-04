# Use Python 3.11 slim for a balance of small size and good compatibility with scientific libraries
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies required by Open3D, py3dtiles, and other C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set default cloud port
ENV PORT=10000
EXPOSE 10000 8000

# Default command (uses shell expansion to respect $PORT from Render, Railway, Cloud Run, etc.)
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-10000}"]

