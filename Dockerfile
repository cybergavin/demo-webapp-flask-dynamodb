# First stage: Build dependencies
FROM python:3.12-alpine AS builder

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev python3-dev

# Set the working directory
WORKDIR /app

# Copy only the dependencies file
COPY requirements.txt /app/

# Install dependencies into a temporary location
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Second stage: Minimal runtime image
FROM python:3.12-alpine

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /install /usr/local

# Copy the application code
COPY . /app/

# Expose the application port
EXPOSE 5000

# Command to run the application
CMD ["python", "demo-catalog-webapp.py"]