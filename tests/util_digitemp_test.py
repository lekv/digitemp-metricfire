#!/usr/bin/env python

import sys, os

if '-i' in sys.argv:
  # create config file
  if '-c' in sys.argv:
    at = sys.argv.index('-c')
    path = os.path.abspath(sys.argv[at+1])
    f = open(path, 'wt')
    f.close()
  else:
    raise Exception("No config path specified")
else:
  # normal operation
  print "17.5"
  print "22.5"
