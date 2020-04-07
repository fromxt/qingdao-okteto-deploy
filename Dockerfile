FROM python:3.6-slim

WORKDIR /usr/src/app
RUN apt update 
RUN apt install -y tesseract-ocr
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY templates ./templates
COPY app.py app.py

EXPOSE 8080

CMD ["python3", "app.py" ]

