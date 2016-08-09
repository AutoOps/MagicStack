# -*- coding:utf-8 -*-
import urllib
import time
import hmac
import requests
import traceback
from MagicStack.api import logger


class API(object):
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.header = self.get_headers(self.username, self.password)


    #proxy的username,password
    def get_headers(self, username, password):
        timestamp = time.time()
        headers = dict()
        data = {
            'X-Timestamp': int(timestamp),
            'X-Username': username
        }
        message = urllib.urlencode(data)
        passwd = hmac.new(password)
        passwd.update(message)
        hexdigest = passwd.hexdigest()
        headers['X-Timestamp'] = int(timestamp)
        headers['X-Username'] = username
        headers['X-Hexdigest'] = hexdigest
        return headers

    def req_post(self, data=None, **kwargs):
        try:
            req = requests.post(self.url, data=data, headers=self.header, **kwargs)
            codes = req.status_code
            msg = req.json()
        except Exception, e:
            logger.error(traceback.format_exc())
            codes = 500
            msg = e.message
        return msg, codes
