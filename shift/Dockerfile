FROM python:3.9-slim
RUN pip install paho-mqtt kubernetes
COPY ./ /app/
WORKDIR /app
CMD ["python", "simulate_shift.py"]
