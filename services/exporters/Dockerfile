FROM python:3.9

ARG WEB3_PROVIDER

WORKDIR /app
COPY . /app

WORKDIR /app/services/exporters
RUN pip install -r requirements.txt

RUN brownie networks modify mainnet host=$WEB3_PROVIDER
