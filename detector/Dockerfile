# Start from a lightweight Python 3.11 base image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements file first (for faster rebuilds)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all detector code into the container
COPY . .

# Run the main daemon when container starts
CMD ["python", "main.py"]
