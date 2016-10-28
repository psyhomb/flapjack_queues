#!/usr/bin/env python2
#
# JSON configuration file example
# Note: master_node has precedence over sentinels, in other words
#       if you define redis master node explicitly program will not use discover method (will ignore sentinels and master_group)
#
# Auto-discover redis master node:
# {
#   "flapjack": {
#     "version": 1
#   },
#   "redis": {
#     "db": 0,
#     "master_group": "mymaster",
#     "sentinels": [
#       {
#         "host": "1.1.1.2",
#         "port": 26379
#       },
#       {
#         "host": "1.1.1.3",
#         "port": 26379
#       },
#       {
#         "host": "1.1.1.4",
#         "port": 26379
#       }
#     ]
#   }
# }
#
# Configuration with explicitly defined redis master node:
# {
#   "flapjack": {
#     "version": 2
#   },
#   "redis": {
#     "db": 0,
#     "master_node": {
#       "host": "1.1.1.1",
#       "port": 6379
#     }
#   }
# }
#
# Client side (requests):
# Show length of all queues
#   curl -s '127.0.0.1:8080/queues' | jq .
#
# Show lenght of specific queue
#   curl -s '127.0.0.1:8080/queue/events' | jq .
#
# Show content of the first event
#   curl -s '127.0.0.1:8080/queue/events?start=0&stop=0' | jq .
#
# Show content of the last event
#   curl -s '127.0.0.1:8080/queue/events?start=-1&stop=-1' | jq .
#
# Show content of the last two events
#   curl -s '127.0.0.1:8080/queue/events?start=-2&stop=-1' | jq .
#
# Delete/Empty 'notifications' queue
#   curl -s -X DELETE 127.0.0.1:8080/queue/notifications
#
# Delete entity
#   curl -s -X DELETE 127.0.0.1:8080/entity/foo.example.com
#
# Create a new event in 'events' queue
#   curl -s -X POST -H 'Content-Type: application/json' --data-binary '@/path/to/event.json' 127.0.0.1:8080/queue/events
#
# event.json:
# Note: All keys are required
# {
#   "entity": "test.example.com",
#   "check": "Memory",
#   "type": "service",
#   "state": "ok",
#   "summary": "MEMORY OK : Mem used: 5.20%, Swap used: 0.00%",
#   "details": "Address:1.2.3.4 Tags:prod,base",
#   "time": 1474239783,
#   "tags": [
#     "prod",
#     "base"
#   ],
#   "initial_failure_delay": 120,
#   "repeat_failure_delay": 120
# }
#


__prog__ = 'flapjack_queues'
__version__ = '0.1'
__author__ = 'Milos Buncic'
__date__ = '2016/09/05'
__description__ = 'Mini HTTP API for Flapjack queues inspection'


import sys
import os
import time
import json
import argparse
from collections import OrderedDict
from redis import StrictRedis
from redis.sentinel import Sentinel
from bottle import get, post, delete, abort, request, response, run


def load_config(config_file):
  """ Load flapjack_queues configuration from the file (output: dict) """
  if os.path.isfile(config_file):
    with open(config_file, 'rU') as f:
      config = json.load(f)
  else:
    print 'File %s doesn\'t exist, please provide a proper configuration file' % config_file
    sys.exit(1)

  return config


class AutoVivification(dict):
  """ Implementation of perl's autovivification feature """
  def __getitem__(self, item):
    try:
      return dict.__getitem__(self, item)
    except KeyError:
      value = self[item] = type(self)()
      return value


class RedisMaster:
  """ Discover and connect to Redis master node """
  def __init__(self, config):
    if 'db' in config:
      self.db = config['db']
    else:
      self.db = 0

    if 'master_node' in config:
      self.master_node = config['master_node']
    else:
      self.master_node = {}

    if 'master_group' in config:
      self.master_group = config['master_group']
    else:
      self.master_group = 'mymaster'

    if 'sentinels' in config:
      self.sentinels = config['sentinels']
    else:
      self.sentinels = [
        {
          'host': '127.0.0.1',
          'port': 26379
        }
      ]

  def discover(self):
    """ Discover redis master node (IP, PORT) (output: tuple) """
    master_node_discovered = False
    for sentinel in self.sentinels:
      try:
        sentinel = Sentinel([(sentinel['host'], sentinel['port'])], socket_timeout=5)
        master_node = sentinel.discover_master(self.master_group)
        master_node_discovered = True
        break
      except:
        continue

    if not master_node_discovered:
      print 'Something went wrong, can\'t discover redis master node, exiting...'
      sys.exit(1)

    return master_node

  def connect(self):
    """ Establish redis connection (output: redis object) """
    master_node_ip_port = self.discover() if not self.master_node else tuple(self.master_node.values())
    master_node_ip = master_node_ip_port[0]
    master_node_port = master_node_ip_port[1]

    retries = 5
    for n in range(1, retries+1):
      try:
        rdb = StrictRedis(host=master_node_ip, port=master_node_port, db=self.db)
        return rdb
      except Exception as e:
        if n == retries:
          print 'Something went wrong (%s), can\'t connect to redis master node, exiting...' % e
          sys.exit(1)
        else:
          time.sleep(3)
          continue


def main():
  parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument('-C', '--config', help='Path to the configuration file', dest='config', action='store', required=True)
  parser.add_argument('-a', '--bind-addr', help='Web server bind IP', default='127.0.0.1', dest='bind_addr', action='store')
  parser.add_argument('-p', '--bind-port', help='Web server bind port', default=8080, type=int, dest='bind_port', action='store')
  parser.add_argument('-w', '--workers', help='Number of web server workers', default=5, type=int, dest='workers', action='store')

  args = parser.parse_args()

  bind_addr = args.bind_addr
  bind_port = args.bind_port
  workers = args.workers
  config = load_config(args.config)

  if 'flapjack' in config and 'version' in config['flapjack']:
    flapjack_version = config['flapjack']['version']
  else:
    flapjack_version = 1

  redis_master = RedisMaster(config['redis'])

  @get('/')
  @get('/queues')
  @get('/queue/<name>')
  def get_queue(name=None):
    """ Get Flapjack queues """
    output = AutoVivification()

    rdb = redis_master.connect()

    if name is None:
      name = ['events', 'notifications', 'email_notifications']
    else:
      name = [name]

      if request.query:
        if 'start' in request.query and 'stop' in request.query:
          try:
            start = int(request.query.start)
            stop = int(request.query.stop)
          except ValueError as e:
            abort(400, 'Bad Request - %s' % e)

          return rdb.lrange(name[0], start, stop)

    for n in name:
      output['flapjack']['queues'][n] = rdb.llen(n)

    return output

  @delete('/queue/<name>')
  def delete_queue(name):
    """ Delete Flapjack queue """
    response.status = 204

    rdb = redis_master.connect()

    if name != 'notifications':
      abort(403, 'Forbidden - Only deletion of notifications queue is currently allowed')

    rdb.delete(name)

  @delete('/entity/<name>')
  def delete_entity(name):
    """ Delete Flapjack entity and related checks """
    response.status = 204

    rdb = redis_master.connect()

    entity_id = rdb.hget('all_entity_ids_by_name', name)
    if not entity_id:
      abort(404, 'Entity not found')

    position, keys = rdb.scan(match='*%s*' % name, cursor=0, count=1000)
    final_keys = keys

    while position != 0:
      position, keys = rdb.scan(match='*%s*' % name, cursor=position, count=1000)
      if keys:
        final_keys += keys

    # Start deleting redis entries
    for key in set(final_keys):
      rdb.delete(key)

    rdb.hdel('all_entity_ids_by_name', name)
    rdb.hdel('all_entity_names_by_id', entity_id)

    for check in [check  for check in rdb.zrange('all_checks', 0, -1)  if name in check]:
      rdb.zrem('all_checks', check)

    if name in rdb.zrange('current_entities', 0, -1):
      rdb.zrem('current_entities', name)

  @post('/queue/<name>')
  def create_event(name):
    """ Create a new flapjack event """
    response.status = 204

    rdb = redis_master.connect()

    # request.MEMFILE_MAX = 102400
    # Maximum size of memory buffer for body in bytes (value cannot be changed, it's a constant)
    #
    # request.json
    # If the Content-Type header is application/json or application/json-rpc, this property holds the parsed content of the request body.
    # Only requests smaller than MEMFILE_MAX are processed to avoid memory exhaustion.
    # Invalid JSON raises a 400 error response.

    if name == 'events' and request.json:
      body = request.json
    else:
      abort(403, 'Forbidden - Wrong queue name "%s", valid queue name is "events"' % name)

    valid = {
      "entity": (str, unicode),
      "check": (str, unicode),
      "type": (str, unicode),
      "state": (str, unicode),
      "summary": (str, unicode),
      "details": (str, unicode),
      "time": (int,),
      "tags": (list,),
      "initial_failure_delay": (int,),
      "repeat_failure_delay": (int,)
    }

    if len(valid.keys()) != len(body.keys()):
      abort(400, 'Bad Request - Invalid number of keys')

    flapjack_event = OrderedDict()
    for key in body.keys():
      if key in valid.keys():
        if type(body[key]) in valid[key]:
          flapjack_event[key] = body[key]
        else:
          abort(400, 'Bad Request - Found invalid key type for key "%s", supported types are %s' % (key, valid[key]))
      else:
        abort(400, 'Bad Request - Found invalid key name "%s"' % key)

    rdb.lpush(name, json.dumps(flapjack_event))
    if flapjack_version == 2:
      rdb.lpush('events_actions', '+')

  # run(host=webserver_ip, port=webserver_port, server='gunicorn', workers=5)
  run(host=bind_addr, port=bind_port, server='paste', use_threadpool=True, threadpool_workers=workers)


if __name__ == '__main__':
  main()
