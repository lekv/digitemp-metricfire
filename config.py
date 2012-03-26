# You can either place your API key into a file called apikey.py *or* you can
# remove the following line and specify the key directly inside the config
# object below
from apikey import api_key

config = {
    # The path to the digitemp binary
    'digitemp': '/usr/bin/digitemp_DS9097',
    # Names for the sensor values returned by digitemp. You must specify
    # exactly as many names as there are sensors.
    'sensors': ['outside', 'inside'],
    # You can either specify your API key here or place it into a file
    # called apikey.py in the same directory.
    'api-key': api_key,
    # The interval in seconds between sensor updates
    'interval': 60,
    # The config file to be used by digitemp. It will be created if it doesn't
    # exist and defaults to digitemp.conf in the current directory.
    'configfile': 'digitemp.conf',
    # The serial port at which the sensors are connected.
    'port': '/dev/ttyS0',
    # This can be used to disabled metricfire asynchronous dns support in case
    # the module is not installed.
    'metricfire_try_adns': False,
}

