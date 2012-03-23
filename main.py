#!/usr/bin/env python

"""
Python DigiTemp Metricfire connector
"""

import subprocess, time, logging, os, sys
import metricfire


config = {
    'digitemp': '/usr/bin/digitemp_DS9097',
    'sensor': '0',
    'name': 'temperature',
    'api-key': 'api_key',
    'interval': 60,
    'configfile': 'digitemp.conf',
    'port': '/dev/ttyS0',
    'metricfire_try_adns': False,
    }

def check_create_config_file():
  port = config.get('port', '/dev/ttyS0')
  path = config.get('configfile', 'digitemp.conf')
  path = os.path.abspath('digitemp.conf')
  if not os.path.exists(path):
    # create the config file using digitemp
    logging.info("Creating config file %s" % path)
    return subprocess.call([config['digitemp'], '-i', '-c', path, '-q', '-s', port])
  else:
    logging.debug("Using existing config file %s" % path)
    return

def get_temperature():
  """Query the temperatur sensor"""
  args = [ '-t', config['sensor'], # query the configured sensor
           '-q',                    # omit the banner
           '-o %C',                 # show only the temperatur in Celsius
           ]
  temp_str = subprocess.check_output([config['digitemp']] + args)
  temp = float(temp_str)
  return temp

if __name__ == '__main__':
  # setup logging
  if '--quiet' in sys.argv:
    logging.basicConfig(level=logging.ERROR)
    #logging.basicConfig(filename='/tmp/metricfire.log', level=logging.DEBUG)
    #logging.debug(time.ctime())
  else:
    logging.basicConfig(level=logging.DEBUG)
  # Check the config file and create it if neccessary
  check_create_config_file()
  # Initialize metrifire API
  logging.debug("Initializing Metricfire API.")
  metricfire.init(config['api-key'], try_adns=config.get('metricfire_try_adns', False))
  while True:
    before = time.time()
    temp = get_temperature()
    logging.debug("Sending temperature: %s" % temp)
    metricfire.send(config['name'], temp)
    now = time.time()

    if '--once' in sys.argv:
      logging.debug("Exiting")
      break

    if now - before > config['interval']:
      logging.info("Interval exceeded.")
    else:
      time.sleep(config['interval'] - (now - before))



