#! /usr/bin/sh
PUSHGATEWAY_URL=https://pushgateway.example.org
USER=prometheus
PASSWORD=prometheus
JOB_NAME=some_job
INSTANCE_NAME=$(hostname)

python "print_top_usage_process.py" --pid $@ | curl -k -u "$USER:$PASSWORD" --data-binary @- "$PUSHGATEWAY_URL/metrics/job/$JOB_NAME/instance/$INSTANCE_NAME"