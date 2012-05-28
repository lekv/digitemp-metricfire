"""Basic Metricfire client."""

# (c) Metricfire 2012

__version__ = "0.4.3"

import os
import sys
import hmac
import time
import types
import socket
import random
import inspect
import hashlib
import binascii
import warnings
import threading

try:
   import simplejson as json
except ImportError:
   import json

_adns_import_exception = None
try:
   import adns
except ImportError, ex:
   _adns_import_exception = ex
   adns = None

# If the user wants to use the module-level interface, this will hold a
# reference to a Client object. Otherwise, the user will use the Client
# object directly.
_module_client = None

class Client:
   """Manages sending metric data points to metricfire. Handles authentication, serialisation and sends data asynchronously."""

   # MF in http://en.wikipedia.org/wiki/E.161
   _default_port = 6333
   _default_server = "udp-api.metricfire.com:%d" % _default_port

   _protoversion = 2

   def __init__(self, key, application = None, server = None, authentication = True, encryption = None, try_adns = True):
      self._host           = None
      self._port           = None
      self._sockaddrs      = []
      self._sockaddrs_age  = 0
      self._sock           = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

      # Attempt to parse the key as a UUID, then Base64 encoded bytes, then fail.
      try:
         # Remove dashes and check the key length.
         rawkey = binascii.unhexlify(key.replace("-", ""))
         assert len(rawkey) == 16
      except (TypeError, AssertionError), ex:
         # Key is not a valid UUID, test base64 decoding next.
         try:
            rawkey = binascii.a2b_base64(key)
            assert len(rawkey) == 32 
         except (binascii.Error, AssertionError), ex:
            # Key is not a valid base64 key either!
            raise ValueError("Unable to parse key in either UUID or Base64 encodings: %s" % key)

      self._key            = rawkey

      self._authentication = authentication
      self._encryption     = encryption
      self._application    = application
      self._sequence       = 0
      self._sessionkey     = None
      self._keyfingerprint = hashlib.md5(self._key).hexdigest()

      # This lock is used (very carefully) later in _format() when updating
      # _sequence and _sessionkey. See _format() for more detail.
      self._lock = threading.Lock()

      if try_adns and adns is None:
         warnings.warn("Could not load python module 'adns'. (%s) This is not necessarily a problem, but Metricfire DNS lookups cannot be guaranteed to be non-blocking. You can disable this warning by using metricfire.init(..., try_adns = False)" % _adns_import_exception, RuntimeWarning, 3)

      # Get application (process) name, if the user didn't specify one.
      if self._application is None or len(self._application) == 0:
         self._application = sys.argv[0] if len(sys.argv[0]) > 0 else 'unknown'

      self._host, self._port = self._parseHostPort(server if server is not None else self._default_server)
   
      # Get system hostname.
      try:
         self._hostname = socket.gethostname()
      except Exception, ex:
         warnings.warn("Could not determine system hostname: %s" % ex, RuntimeWarning, 2)
         self._hostname = "unknown"
      
      if adns is not None:
         self._adns_resolver = adns.init()
      else:
         self._adns_resolver = None
      self._adns_query = None
      
      # Check if we were given an IP address instead of a hostname.
      try:
         socket.inet_aton(self._host)
         self._sockaddrs = [(self._host, self._port)]
      except socket.error: 
         # Otherwise, fire off an asynchronous DNS query now to resolve it.
         # We do this so _send() doesn't have to block.
         self._queryDNS()

   def __del__(self):
      # Attempt to flush the buffer, if any exists.
      # TODO
      pass

   def _generateSessionKey(self):
      return os.urandom(16)

   def _parseHostPort(self, hostport):
      """Returns a (host, port) tuple from a colon-separated host and port string, with an optional port."""

      components = hostport.split(":")
      if len(components) == 1:
         return components[0], self._default_port
      elif len(components) == 2:
         return components[0], int(components[1])
      else:
         raise ValueError("Invalid host:port spec: %s" % hostport)

   def _queryDNS(self):
      """Async dns query""" # TODO
      if self._adns_resolver is not None:
         self._adns_query = self._adns_resolver.submit(self._host, 1)
      else:
         for (family, socktype, proto, canonname, sockaddr) in socket.getaddrinfo(self._host, self._port):
            self._sockaddrs.append(sockaddr)

   def _format(self, datapoints):
     
      # Locking is used very carefully here because threads can interfere with
      # the modification of sequence numbers and session keys.

      # Using locking here doesn't break the non-blocking sending contract
      # because:
      # * Reading/writing basic types does not block
      # * Calling os.urandom() does not block as it reads from /dev/urandom
      #   which, on UNIX-like systems, is a non-blocking entropy source.
      #   In comparison, /dev/random can block while waiting for entropy.
      # See http://docs.python.org/library/os.html#os.urandom and urandom (4)
      # Also, not using "with self.lock:" syntax for python2.5 compatibility :(
      self._lock.acquire()
      self._sequence += 1
      if self._sessionkey is None or self._sequence >= 2**32:
         self._sequence = 1
         self._sessionkey = os.urandom(16)
      sequence = self._sequence
      sessionkey = self._sessionkey
      self._lock.release()

      # TODO Pre-fragmentation for multiple messages?

      body = {'h': self._hostname, 'a': self._application, 'm': []}
      for (metric, value, timestamp) in datapoints:
         body['m'].append((metric, value, timestamp))

      body_json = json.dumps(body)

      if self._encryption:
         # TODO Body crypto!
         pass

         # TODO Compress body?

      header = {'v': self._protoversion, 'f': self._keyfingerprint, 's': binascii.hexlify(sessionkey), 'q': sequence}

      if self._authentication:
         # Calculate a HMAC for the body, including a session key and a sequence
         # number to prevent replay attacks.
         auth = hmac.HMAC(self._key, digestmod = hashlib.sha256)
         auth.update(sessionkey)
         auth.update(str(sequence))
         auth.update(body_json)
         header['a'] = auth.hexdigest()
  
      header_json = json.dumps(header)

      # Return a complete message.
      return header_json + "\n" + body_json

   def send(self, metric, value, timestamp = None):
      """Send a metric and a value to Metricfire without blocking. If a UNIX timestamp is supplied, the value will be recorded as happening at that time. Otherwise, the current time is assumed."""
      message = self._format([(metric, value, timestamp)])
      self._send(message)

   def _send(self, content):
      """The meat of sending a metric message. Checks for DNS query results and chooses a random socket to send it to.""" # TODO

      # If we previously started a DNS query....
      if self._adns_query is not None:
         # ... check it for results.
         try:
            (status, cname, expires, rrs) = self._adns_query.check()
            # TODO Check status, or just use the length of the rrs?
            if len(rrs) > 0:
               for addr in rrs:
                  self._sockaddrs.append((addr, self._port))
   
            self._adns_query = None
         except adns.NotReady:
            pass # Check it next time.
            # TODO Try to buffer the content to send next time.
            #print "Not sent." # XXX
      else:
         # TODO Repeat the DNS query after the expires time.
         pass

      if len(self._sockaddrs) > 0:
         before = time.time()
         # Pick a sockaddr at random.
         self._sock.sendto(content, random.choice(self._sockaddrs))
         after = time.time()
         #print "Send to (%s, %d) took %fs" % (self._sockaddrs, self._port, after - before) # TODO
      else:
         pass
         # TODO buffer

def init(*args, **kwargs):
   """Initialise the metricfire module by providing your secret key, an optional name/label for this application, and an optional hostname to send metric data to. See help(metricfire.Client) for supported arguments."""
   global _module_client
   _module_client = Client(*args, **kwargs)

def send(metric, value, timestamp = None):
   """Send a metric and a value to Metricfire without blocking. If a UNIX timestamp is supplied, the value will be recorded as happening at that time. Otherwise, the current time is assumed."""
   global _module_client
   if _module_client is None:
      warnings.warn("metricfire.send() called without metricfire.init() being called first. Either call metricfire.init(), or use a metricfire.Client() object. Metric message dropped.", RuntimeWarning, 2)
   else:
      _module_client.send(metric, value, timestamp)

def measure(prefix = None):
   """Decorate a function whose calling frequency and running times should be reported to Metricfire. Optionally set a prefix for the resulting metric name. The metric name takes the form of: [prefix.][module.][class.]function"""
   
   # If the prefix is actually a function, we're being called in argless mode.
   # (Like: @metricfire.measure, instead of @metricfire.measure(...))
   if type(prefix) == types.FunctionType:
      func = prefix
      argless = True
      prefix = None
   else:
      argless = False

   def decorator(func):
      # This is a somewhat odd way of maintaining state between call_func calls.
      # We'd like to maintain state because we want to memoise the computed metric
      # name. By defining a dict outside the scope of call_func, it will be
      # available inside call_func and the contents can be changed, though it 
      # cannot itself be reassigned.
      # Better solutions welcomed!
      state = {'metric': None}

      def call_func(*args, **kwargs):

         if state['metric'] is None:
            # No metricname memoised yet.

            # Try to detect the name of the class this function might belong to.
            try:
               # If the first argument has an attribute with the same name as the
               # function then try to find the name of the class.
               clsname = getattr(args[0], func.__name__).im_class.__name__
            except (AttributeError, IndexError), ex:
               clsname = None

            # Build the metric name.
            metric = []
            if prefix is not None:
               metric.append(prefix)
            if func.__module__ not in ['__main__', None]:
               metric.append(func.__module__)
            if clsname is not None:
               metric.append(clsname)
            metric.append(func.__name__)
         
            # Memoise the metricname into the context of the call_func wrapper so
            # it is available on the next call.
            state['metric'] = ".".join(metric)

         # Call the user's function and record how long it takes to complete.
         before = time.time()
         result = func(*args, **kwargs)
         duration = time.time() - before

         # Tell Metricfire all about it.
         send(state['metric'], duration)

         return result
      return call_func
   
   # If the user is using the decorator in argless mode (@foo, not @foo())
   # then execute the first layer of the decorator and return the inner call_func.
   if argless:
      return decorator(func)
   else:
      # Otherwise, return the outer decorator function.
      return decorator

class Timer:
   """A simple helper class for basic timing. Accepts an optional prefix that will appear at the beginning of all metric names. Can also be used with 'with' syntax."""

   _start_time = None
   _metric = None
   _prefix = None

   def __init__(self, prefix = None):
      self._prefix = prefix

   def start(self, metric = None, restart = False):
      """Start timing. Tries to autodetect the name of the caller."""
      metric_pieces = []
      if self._prefix is not None:
         metric_pieces.append(self._prefix)
      
      if metric is not None:
         if len(metric) != 0:
            metric_pieces.append(metric)
      else:
         # Attempt to detect the name of the caller.
         # Alter the frame we look at based on the restart arg because
         # start() is called from restart() and might hide the real caller.
         frame = 2 if restart else 1
         caller = inspect.stack()[frame][3]
         metric_pieces.append(caller)

      self._metric = ".".join(metric_pieces)
      self._start_time = time.time()

   def restart(self, metric = None):
      """Restart a running timer. Sends a timing report and immediately starts timing again."""
      self.stop()
      self.start(metric, restart = True)

   def stop(self):
      """If previously start()ed or restart()ed, stop() stops timing and sends a report."""
      if self._start_time is not None:
         send(self._metric, time.time() - self._start_time)
         self._start_time = None

   def cancel(self):
      """Stop a running timer without sending a report."""
      self._start_time = None
      
   def __del__(self):
      """Stop timing and reports a timed value when this object is destroyed."""
      if self._start_time is not None:
         self.stop()

   def __enter__(self):
      # When used in 'with' mode, don't try to autodetect anything and don't use a metric name.
      self.start(metric = "")
      return self

   def __exit__(self, *args):
      self.stop()


