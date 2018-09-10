FROM python:3.5  
ENV PYTHONUNBUFFERED 1  
RUN mkdir /data_dispatcher
WORKDIR /data_dispatcher
ADD . .
RUN pip3 install -r requirements.pip