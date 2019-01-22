FROM python:3-alpine

MAINTAINER M. Hamzah Khan <hamzah@hamzahkhan.com>

RUN apk -U upgrade \
 && apk add -t build-dependencies \
    build-base \
 && apk add tini \
 && rm -rf /tmp/* /var/cache/apk/*

WORKDIR /app
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -e .

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["/app/docker/start.sh"]
