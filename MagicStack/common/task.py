#! /usr/bin/env python
# -*- coding:utf-8 -*-

from apscheduler.Schedulers.background import BackgroundScheduler
from apscheduler.events import *
import Queue
from interface import APIRequest
from MagicStack.api import get_object
from models import Task

queue_jobs = Queue.Queue()


def get_jobs(request):
    jobs = Task.objects.filter(status='running', username=request.user.username)
    for item in jobs:
        queue_jobs.put(dict(task_name=item.name, url=item.url, uuid=item.uuid))


def exec_jobs(username, password):
    if queue_jobs.qsize() > 0:
        job = queue_jobs.get()
        schedu = TaskScheduler(username, password)
        res = schedu.get_result(job['url'])
        tk = get_object(Task, name=res['task_name'],uuid=job['uuid'])
        tk.status = res['status']
        if 'content' in res.keys():
            tk.content = res['content']
        tk.save()
        return res


def my_listener(event):
    if event.exception:
        pass
    else:
        pass


class TaskScheduler(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_result(self, url, request):
        req = APIRequest(url, self.username, self.password)
        res = req.req_get()
        tk = get_object(Task, name=res['task_name'])
        tk.status = res['status']
        tk.username = request.user.username
        tk.save()
        return res


if __name__ == '__main__':
    schedu = BackgroundScheduler()
    schedu.add_jobs(get_jobs, 'interval', seconds=5)
    schedu.add_jobs(exec_jobs, 'interval', seconds=10)
    schedu.add_listener(my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    schedu.start()







