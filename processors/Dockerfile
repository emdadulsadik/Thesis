FROM python:3.9-slim
RUN pip install paho-mqtt
COPY ./ /app/
WORKDIR /app
CMD ["python", "./processors/iot_processor.py"]

