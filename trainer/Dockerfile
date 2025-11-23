FROM python:3.9-slim
RUN pip install paho-mqtt pandas xgboost scikit-learn joblib
COPY ./ /app/
WORKDIR /app
CMD ["sh", "-c", "python label_features.py && python train_xgb.py"]
