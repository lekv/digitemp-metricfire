import unittest

def test():
  tests = unittest.defaultTestLoader.discover('tests')
  runner = unittest.TextTestRunner()
  res = runner.run(tests)
