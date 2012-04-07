import unittest
import os

def test():
  if not os.path.isdir('tests/tmp'):
    os.mkdir('tests/tmp')
  tests = unittest.defaultTestLoader.discover('tests')
  runner = unittest.TextTestRunner()
  res = runner.run(tests)
