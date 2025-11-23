FROM python:3.9-slim
RUN pip install paho-mqtt psutil
COPY ./ /app/
WORKDIR /app
CMD ["python", "iot_processor.py"]

