# -*- coding:utf-8 -*-
# Copyright (c) 2016 MagicStack
#
# Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import Queue
import threading
from MagicStack.api import logger


class WorkManager(object):
    """
    任务管理类
    work_num: 任务数量
    thread_num: 线程数量
    """
    def __init__(self, proxy_list,thread_num=2):
        self.work_queue = Queue.Queue()
        self.threads = []
        self.thread_num = thread_num
        self.proxys = proxy_list

    def init_thread_pool(self):
        """
        初始化线程
       """
        for i in range(self.thread_num):
            self.threads.append(Work(self.work_queue))

    def init_work_queue(self, func, *args, **kwags):
        """
        初始化工作队列
       """
        for item in self.proxys:
            kwags['proxy'] = item
            self.work_queue.put((func, args, kwags))


class Work(threading.Thread):
    def __init__(self, work_queue):
        threading.Thread.__init__(self)
        self.work_queue = work_queue
        self.setDaemon(False)     # 主线程结束后,子线程继续运行
        self.start()

    def run(self):
        while True:
            try:
                do_func, args, kwargs = self.work_queue.get(block=False)     # 任务异步出队，Queue内部实现了同步机制
                do_func(*args, **kwargs)
                self.work_queue.task_done()     # 通知系统任务完成
            except Exception as e:
                logger.error(e)
                break

