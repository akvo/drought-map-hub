FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Set the default working directory (optional)
# WORKDIR /app

# Command can be overridden by docker-compose
CMD ["python", "STEP_0000_execute_all_steps.py"]
