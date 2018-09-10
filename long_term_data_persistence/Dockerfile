FROM python:3.5  
ENV PYTHONUNBUFFERED 1  
RUN mkdir /long_term_data_persistence
WORKDIR /long_term_data_persistence
ADD . .
RUN pip3 install -r requirements.pip