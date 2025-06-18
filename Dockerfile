# Multi-stage build for VLANVision
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 vlanvision

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/vlanvision/.local

# Copy application code
COPY --chown=vlanvision:vlanvision . .

# Create necessary directories
RUN mkdir -p /app/instance && \
    chown -R vlanvision:vlanvision /app

# Switch to non-root user
USER vlanvision

# Add local bin to PATH
ENV PATH=/home/vlanvision/.local/bin:$PATH

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=src.ui.app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')" || exit 1

# Run the application
CMD ["python", "-m", "src.main"]