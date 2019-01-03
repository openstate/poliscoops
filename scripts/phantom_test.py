#!/usr/bin/env python
import sys

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

driver = webdriver.Remote(
    command_executor='http://phantomjs:8910',
    desired_capabilities=DesiredCapabilities.PHANTOMJS)

if len(sys.argv) > 1:
    url = sys.argv[1]
else:
    url = 'http://gbachtkarspelen.nl/2018/06/09/de-rust-is-terug-in-de-gemeenteraad/'
driver.get(url)

with open('detect.js') as in_file:
    detect_js = in_file.read()

detect_js += """
window._html_output = 'blah';

// define
var _detect = {
  'callbacks': {
  'finished': function (_result) { window._html_output = _result._html; },
 },
 'window': window,
 'jQuery': window.jQuery
};
_detect = initClearlyComponent__detect(_detect);
_detect.start();
"""

driver.execute_script(detect_js)

# print driver.get_log('browser')

print driver.execute_script('return window._html_output;')
driver.quit()
