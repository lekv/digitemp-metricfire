#!/usr/bin/env python

import unittest, subprocess, os

class TestDigitempTest(unittest.TestCase):
  def setUp(self):
    self.binary = os.path.abspath('tests/util_digitemp_test.py')

  def test_normal(self):
    output = subprocess.check_output([self.binary])
    # Output was present
    self.assertIsNotNone(output)
    values = map(float, output.split())
    # Check for one of the magic values
    self.assertIn(17.5, values)

  def test_create_config_file(self):
    # path of config file to be created
    path = os.path.abspath('tests/tmp/digitemp.conf')
    # remove path if already present
    if os.path.exists(path):
      os.remove(path)
    self.assertFalse(os.path.exists(path))
    # Let digitemp create the file
    subprocess.call([self.binary, '-i', '-c', path])
    # Verify the file is there
    self.assertTrue(os.path.exists(path))
    os.remove(path)

