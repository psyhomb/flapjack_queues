flapjack_queues mini HTTP API
=============================

About
-----
This API exposes some interesting features that regular Flapjack API doesn't have
  - Watch length of `events`, `notifications` and `email_notifications` queues
  - See events that are still in the queue
  - Purge any of the mentioned queues if any of them is overflowed with events
  - Permanently delete all checks for named entity (current Flapjack API on version 1.6 will allow you only to disable checks)
  - Push events directly to `events` queue on master Redis


Requirements
------------
This API requires python2.7 and some additional modules that are specified in the requirements.txt file:

```
bottle==0.12.9
Paste==2.0.3
redis==2.10.5
six==1.10.0
```


Installation
------------
Install pew (python environment wrapper)
```
pip2 install pew
```

Create dirs
```
mkdir -p /data/pew/{virtualenvs,flapjack_queues}
mkdir -p /var/log/flapjack_queues
```

Create a new virtualenv for flapjack_queues.py
```
WORKON_HOME="/data/pew/virtualenvs" pew new -a /data/pew/flapjack_queues -r requirements.txt flapjack_queues
```

Enter virtualenv
```
WORKON_HOME=/data/pew/virtualenvs pew workon flapjack_queues
```


Supervisor configuration file `/etc/supervisor/conf.d/flapjack_queues.conf`
```
[program:flapjack_queues]
command=/data/pew/%(program_name)s/%(program_name)s.py -C /data/pew/%(program_name)s/%(program_name)s.json -a 0.0.0.0 -p 8080
numprocs=1
autostart=true
autorestart=true
startsecs=3
startretries=3
;environment=PATH="/data/pew/virtualenvs/%(program_name)s/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",HOME="/data/pew/%(program_name)s",WORKON_HOME="/data/pew/virtualenvs"
environment=PATH="/data/pew/virtualenvs/%(program_name)s/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",HOME="/data/pew/%(program_name)s"
priority=999
directory=/data/pew/%(program_name)s
user=root
redirect_stderr=true
stdout_logfile_maxbytes=100MB
stdout_logfile_backups=10
stdout_logfile=/var/log/%(program_name)s/%(program_name)s.log
```

Add and start service
```
supervisorctl add flapjack_queues
supervisorctl update flapjack_queues
```

Configuration
-------------
JSON configuration file example

**Note**: master_node has precedence over sentinels, in other words
      if you define redis master node explicitly program will not use discover method (will ignore sentinels and master_group)

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
curl -s '127.0.0.1:8080/queues' | jq .
```

Show lenght of specific queue
```
curl -s '127.0.0.1:8080/queue/events' | jq .
```

Show content of the first event
```
curl -s '127.0.0.1:8080/queue/events?start=0&stop=0' | jq .
```

Show content of the last event
```
curl -s '127.0.0.1:8080/queue/events?start=-1&stop=-1' | jq .
```

Show content of the last two events
```
curl -s '127.0.0.1:8080/queue/events?start=-2&stop=-1' | jq .
```

Delete/Empty `notifications` queue
```
curl -s -X DELETE 127.0.0.1:8080/queue/notifications
```

Delete entity
```
curl -s -X DELETE 127.0.0.1:8080/entity/foo.example.com
```

Create a new event in `events` queue
```
curl -s -X POST -H 'Content-Type: application/json' --data-binary '@/path/to/event.json' 127.0.0.1:8080/queue/events
```

event.json:

**Note**: All keys are required
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
