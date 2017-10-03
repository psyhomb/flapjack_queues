flapjack_queues mini HTTP API
=============================

About
-----
This API exposes some interesting features that regular Flapjack API doesn't have
  - Print length of `events`, `notifications` and `email_notifications` queues
  - Show events that are still in the queue
  - Purge any of the mentioned queues if any of them is overflowed with events
  - Permanently delete all checks for named entity (current Flapjack API on version 1.6 will allow you only to disable checks)
  - Push events directly to `events` queue on master Redis


Requirements
------------
This API requires python2.7 and some additional modules that are specified in the `requirements.txt` file:

```
bottle==0.12.9
Paste==2.0.3
redis==2.10.5
six==1.10.0
```


Installation
------------

#### Supervisor

Install `pew` (python environment wrapper)
```
pip2 install pew
```

Create dirs
```
mkdir -p /data/pew/virtualenvs
mkdir -p /etc/flapjack_queues
mkdir -p /var/log/flapjack_queues
```

Clone repo
```
git clone https://<fqdn>/<username>/flapjack_queues.git /data/pew/flapjack_queues
cd /data/pew/flapjack_queues
```

Create a new virtualenv for `flapjack_queues`
```
WORKON_HOME="/data/pew/virtualenvs" pew new -a /data/pew/flapjack_queues -r requirements.txt flapjack_queues
```

Enter virtualenv (previous commad will enter virtualenv at the end)
```
WORKON_HOME=/data/pew/virtualenvs pew workon flapjack_queues
```

Copy and modify `flapjack_queues` configuration file
```
cp /data/pew/flapjack_queues/flapjack_queues.json /etc/flapjack_queues/flapjack_queues.json
```

Copy and modify `supervisor` configuration file
```
cp /data/pew/flapjack_queues/supervisor/flapjack_queues.conf /etc/supervisor/conf.d/flapjack_queues.conf
```

Add and start service
```
supervisorctl reread
supervisorctl add flapjack_queues
```

#### Docker

Docker build and run
```
docker build -t flapjack_queues .
docker run -itd --name flapjack_queues -p 8080:8080 flapjack_queues
```


Configuration
-------------
JSON configuration file example

**Note**: `master_node` has precedence over sentinels, in other words
      if you define redis master node explicitly program will not use discover method (will ignore sentinels and `master_group`)

Auto-discover redis master node:
```json
{
  "flapjack": {
    "version": 1
  },
  "redis": {
    "db": 0,
    "master_group": "mymaster",
    "sentinels": [
      {
        "host": "1.1.1.2",
        "port": 26379
      },
      {
        "host": "1.1.1.3",
        "port": 26379
      },
      {
        "host": "1.1.1.4",
        "port": 26379
      }
    ]
  }
}
```

Configuration with explicitly defined redis master node:
```json
{
  "flapjack": {
    "version": 2
  },
  "redis": {
    "db": 0,
    "master_node": {
      "host": "1.1.1.1",
      "port": 6379
    }
  }
}
```


Usage
-----

Client side (requests):

Show length of all queues
```
curl -s 'http://127.0.0.1:8080/queues' | jq .
```

Show lenght of designated queue
```
curl -s 'http://127.0.0.1:8080/queue/events' | jq .
```

Show content of the first event
```
curl -s 'http://127.0.0.1:8080/queue/events?start=0&stop=0' | jq .
```

Show content of the last event
```
curl -s 'http://127.0.0.1:8080/queue/events?start=-1&stop=-1' | jq .
```

Show content of the last two events
```
curl -s 'http://127.0.0.1:8080/queue/events?start=-2&stop=-1' | jq .
```

Delete/Purge `notifications` queue
```
curl -s -X DELETE 'http://127.0.0.1:8080/queue/notifications'
```

Delete entity
```
curl -s -X DELETE 'http://127.0.0.1:8080/entity/foo.example.com'
```

Create a new event in the `events` queue
```
curl -s -X POST -H 'Content-Type: application/json' --data '@/path/to/event.json' 'http://127.0.0.1:8080/queue/events'
```

event.json:

**Note**: All keys are mandatory
```json
{
  "entity": "test.example.com",
  "check": "Memory",
  "type": "service",
  "state": "ok",
  "summary": "MEMORY OK : Mem used: 5.20%, Swap used: 0.00%",
  "details": "Address:1.2.3.4 Tags:prod,base",
  "time": 1474239783,
  "tags": [
    "prod",
    "base"
  ],
  "initial_failure_delay": 120,
  "repeat_failure_delay": 120
}
```


License and Authors
-------------------
**Author**: Milos Buncic
