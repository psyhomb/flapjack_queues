FROM alpine:3.2

RUN mkdir -p /data/flapjack_queues /etc/chaperone.d && apk add --update python3 python py-pip && pip3 install chaperone
COPY flapjack_queues.* /data/flapjack_queues/
COPY requirements.txt /data/flapjack_queues/
COPY docker/chaperone.conf /etc/chaperone.d/chaperone.conf
RUN pip2 install -r /data/flapjack_queues/requirements.txt

ENTRYPOINT ["/usr/bin/chaperone"]
