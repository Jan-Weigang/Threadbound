# Use Python 3.12 slim image
FROM python:3.12-slim

WORKDIR /usr/src/app/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    TZ=Europe/Berlin


# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip list
    
# Set up timezone and print debugs
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    echo $PATH

# Copy project
COPY . .

EXPOSE 5000

WORKDIR /usr/src/app

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]


