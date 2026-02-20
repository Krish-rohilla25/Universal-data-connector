FROM python:3.11-slim

WORKDIR /app

# Install dependencies separately so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port uvicorn listens on
EXPOSE 8000

# Run the server; host 0.0.0.0 makes it reachable outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
