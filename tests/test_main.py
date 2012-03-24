import unittest, sys, os, mock

import logging

logging.basicConfig(level=logging.ERROR)

sys.path.append(os.getcwd())
import main

class TestMain(unittest.TestCase):
  def setUp(self):
    main.config['digitemp']   = os.path.abspath('tests/util_digitemp_test.py')
    main.config['configfile'] = os.path.abspath('tests/tmp/digitemp.conf')
    main.config['configfile'] = os.path.abspath('tests/tmp/digitemp.conf')
    main.config['sensors']    = ['outside', 'inside']

  def test_self(self):
    self.assertIsNotNone(main.config)
    self.assertEqual(main.config['digitemp'], os.path.abspath('tests/util_digitemp_test.py'))

  @mock.patch('metricfire.send')
  def test_mock(self, mf_mock):
    main.metricfire.send("foo", "bar")
    self.assertTrue(mf_mock.called)

  def test_check_create_config_file(self):
    path = main.config['configfile']
    self.assertIn('tmp', path)
    if os.path.exists(path):
      os.remove(path)
    
    # Make sure, config file doesn't exist
    self.assertFalse(os.path.exists(path))
    main.check_create_config_file()
    # Make sure, config file exists
    self.assertTrue(os.path.exists(path))
    os.remove(path)

  def test_get_temperatures(self):
    # The configured digitemp path must contain the word test to indicate, it's a mockup
    self.assertIn('test', main.config['digitemp'])
    values = main.get_temperatures()
    self.assertIn(17.5, values)
    self.assertIn(22.5, values)

  def test_send_temperatures(self):
    # mock metricfire.send
    with mock.patch('metricfire.send') as mf_mock:
      # call send_temperatures with array of values
      values = [10, 20]
      main.send_temperatures(values)
      # check send() was called properly
      expected = map(mock.call, main.config['sensors'], values)
      mf_mock.assert_has_calls(expected)

  @mock.patch('main.send_temperatures')
  @mock.patch('main.get_temperatures')
  def test_send_receive(self, get_mock, send_mock):
    values = [10, 20]
    get_mock.return_value = values
    main.send_receive()
    # test that get_temperatures gets called
    get_mock.assert_called_once_with()
    # test that send_temperatures gets called
    send_mock.assert_called_once_with(values)

  def test_main_once(self):
    # TODO: Make main() testable
    pass

