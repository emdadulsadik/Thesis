FROM python:3.9-slim
RUN pip install paho-mqtt kubernetes xgboost pandas numpy
COPY ./ /app/
WORKDIR /app
CMD ["python", "ai_scheduler.py"]
