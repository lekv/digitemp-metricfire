#!/usr/bin/env python

"""
#Python DigiTemp Metricfire connector

This program queries temperature sensors and upload the data to metricfire via
its python API.  It will run until terminated by ctrl-c. Alternatively have a
look at the --once and --quiet command line switches to run under cron.

## Configuration
For the configuration of the various runtime parameters, have a look at the
config object below.

## Supported command line switches:
  --once      : Run only once and exit after uploading the data.
  --quiet     : Don't output anything below ERROR level.
"""

import subprocess, time, logging, os, sys
import metricfire

from config import config

def check_create_config_file():
  """Check for the presence of the config file and create it, if it is missing."""
  port = config.get('port', '/dev/ttyS0')
  path = config.get('configfile', 'digitemp.conf')
  path = os.path.abspath(path)
  if not os.path.exists(path):
    # create the config file using digitemp
    logging.info("Creating config file %s" % path)
    return subprocess.call([config['digitemp'], '-i', '-c', path, '-q', '-s', port])
  else:
    logging.debug("Using existing config file %s" % path)
    return

def get_temperatures():
  """Query the temperatur sensor.
  
   This returns a list of temperatures converted to float values."""
  # Config file path
  path = config.get('configfile', 'digitemp.conf')
  path = os.path.abspath('digitemp.conf')
  args = [ '-a',                    # Query all sensors
           '-c', path,              # config file path
           '-q',                    # omit the banner
           '-o %C',                 # show only the temperatur in Celsius
           ]
  temp_str = subprocess.check_output([config['digitemp']] + args)
  temps = map(float, temp_str.split())
  return temps

def send_temperatures(values):
  """Send a list of temperatures to the metricfire API.

  This maps the temperatures to names in the config['sensors'] list.
  """
  for name, temp in zip(config['sensors'], values):
    # Send the value
    logging.debug("Sending temperature: %s" % temp)
    metricfire.send(name, temp)

def send_receive():
  """Wrap getting and sending the values once."""
  values = get_temperatures()
  send_temperatures(values)

def main():
  # setup logging
  if '--quiet' in sys.argv:
    logging.basicConfig(level=logging.ERROR)
    #logging.basicConfig(filename='/tmp/metricfire.log', level=logging.DEBUG)
    #logging.debug(time.ctime())
  else:
    logging.basicConfig(level=logging.DEBUG)

  # Make sure, a digitemp configfile exists
  check_create_config_file()
  # Initialize metrifire API
  logging.debug("Initializing Metricfire API.")
  metricfire.init(config['api-key'], try_adns=config.get('metricfire_try_adns', False))
  while True:
    before = time.time()
    send_receive()
    now = time.time()

    if '--once' in sys.argv:
      logging.debug("Exiting")
      break

    if now - before > config['interval']:
      logging.info("Interval exceeded.")
    else:
      time.sleep(config['interval'] - (now - before))

if __name__ == '__main__':
  main()
