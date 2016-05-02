# -*- coding:utf-8 -*-
import urllib2
import urllib
import time
import hmac
import logging
import json
import requests

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
        headers = dict()
        data = {
            'X-Timestamp':int(timestamp),
            'X-Username':username
        }
        message = urllib.urlencode(data)
        passwd = hmac.new(password)
        passwd.update(message)
        hexdigest = passwd.hexdigest()
        headers['X-Timestamp'] = int(timestamp)
        headers['X-Username'] = username
        headers['hexdigest'] = hexdigest
        headers['Content-Type'] = 'application/json'
        return headers

    def req_get(self):
        msg = ''
        try:
            req = requests.get(self.url, headers=self.header)
            if req.status_code == requests.codes.ok:
                recv = json.loads(req)
                msg = recv['message']
        except Exception as e:
                logger.error(e)
        return msg

    def req_post(self, data):
        msg = ''
        try:
            req = requests.get(self.url, headers=self.header, data=data)
            if req.status_code == requests.codes.ok:
                recv = json.loads(req)
                msg = recv['message']
        except Exception as e:
                logger.error(e)
        return msg

    def req_put(self, data):
        msg = ''
        try:
            req = requests.get(self.url, headers=self.header, data=data)
            if req.status_code == requests.codes.ok:
                recv = json.loads(req)
                msg = recv['message']
        except Exception as e:
                logger.error(e)
        return msg

