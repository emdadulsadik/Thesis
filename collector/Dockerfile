FROM python:3.9-slim
RUN pip install paho-mqtt
RUN apt-get update && apt-get install -y vim iputils-ping nano netcat-openbsd && rm -rf /var/lib/apt/lists/*
COPY ./ /app/
WORKDIR /app
CMD ["python", "collect_training_data.py"]
