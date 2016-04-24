# -*- coding:utf-8 -*-
import urllib2
import urllib
import time
import hmac
import logging
import json

logger = logging.getLogger('interface')
logger.setLevel(logging.DEBUG)


class APIRequest(object):
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.header = APIRequest.get_headers(self, self.username, self.password)


    #proxy的username,password
    def get_headers(self, username, password):
        timestamp = time.time()
        headers = dict(username=username, timestamp=timestamp)
        data = {
            'X-Timestamp':int(timestamp),
            'X-Username':username
        }
        message = urllib.urlencode(data)
        passwd = hmac.new(password)
        passwd.update(message)
        hexdigest = passwd.hexdigest()
        headers['hexdigest'] = hexdigest
        headers['Content-Type'] = 'application/json'
        return headers

    def req_get(self):
        request = urllib2.Request(self.url)
        request.add_header(**self.header)
        try:
            result = urllib2.urlopen(request)
        except Exception as e:
            logger.error(e)
        else:
            response = json.loads(result.read())
        return response

    def req_post(self, data):
        request = urllib2.Request(self.url, data)
        request.add_header(**self.header)
        try:
            result = urllib2.urlopen(request)
        except Exception as e:
            logger.error(e)
        else:
            response = json.loads(result.read())
        return response

