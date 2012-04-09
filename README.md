#Python DigiTemp Metricfire connector

This program queries temperature sensors and upload the data to
[metricfire](http://metricfire.com) via its python API.  It will run until
terminated by ctrl-c. Alternatively have a look at the --once and --quiet
command line switches to run under cron.

## Requirements
 - You need to have [Digitemp] installed and working.
 - To run the included unit tests, you need [Fabric] installed.

## Building the sensors
TODO: Link to websites describing the process.

## Configuration
The various runtime parameters are set in config.py. The api-key can also be
specified in an own file. The various configuration parameters are documented
in config.py itself.

## Supported command line switches:
- --once      : Run only once and exit after uploading the data.
- --quiet     : Don't output anything below ERROR level.

## Running with cron

The following line can be entered into your crontab (hint: run `crontab -e`)
and will have cron call the script once per minute. Errors during execution
will show up in your syslog and will usually be sent to you via email.

    * * * * * cd PATH_WHERE_YOU_CHECKED_OUT; ./main.py --quiet --once;

## Unittests
You can run the included unit tests, by calling `fab test` in the top level
directory. However you need mock version >= 0.8 for the tests to run.
