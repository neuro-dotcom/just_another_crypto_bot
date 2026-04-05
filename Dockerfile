# Use a lightweight Python image
FROM python:3.11-slim

# Keep Python from buffering logs so we can see errors in real-time
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the default Hugging Face port
EXPOSE 7860

# Run the bot
CMD ["python", "main.py"]