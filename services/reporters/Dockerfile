FROM python:3.9

ARG DATAPANE_TOKEN

WORKDIR /app
COPY . /app

WORKDIR /app/services/reporters
RUN pip install -r requirements.txt

# install cron
RUN apt-get update && apt-get install -y cron
RUN echo "DATAPANE_TOKEN=${DATAPANE_TOKEN}" > temp \
  && cat cronjobs >> temp \
  && mv temp /etc/cron.d/cronjobs \
  && chmod 0644 /etc/cron.d/cronjobs \
  && crontab /etc/cron.d/cronjobs

WORKDIR /app
RUN touch /var/log/cron.log
CMD cron && tail -f /var/log/cron.log