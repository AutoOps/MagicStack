#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2016 MagicStack 
#
#   Licensed under the Apache License, Version 2.0 (the "License");
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

from models import Task
from common.interface import APIRequest
from MagicStack.api import *
import traceback


def get_task_info_from_proxy(task):
    # 调用proxy接口
    api = APIRequest('{0}/v1.0/job_task/{1}?limit=1'.format(task.task_proxy.url, task.task_uuid),
                     task.task_proxy.username,
                     CRYPTOR.decrypt(task.task_proxy.password))
    result, code = api.req_get()
    if code != 200:
        # 获取失败，下次继续获取
        result = {}
    else:
        result = result['result']
    return result


def get_task_exec_info():
    """
        更新任务，最后执行记录
    """
    task_states = {
        'complete': '完成',
        'failed': '失败',
        'running': '执行中'
    }
    try:
        logger.info("start get task exec info >>>>>>")
        tasks = Task.objects.filter(is_get_last='00')

        for task in tasks:
            try:
                result = get_task_info_from_proxy(task)
                if result:
                    # job是否已经在触发器范围之外
                    job = result['job']
                    # 最后执行消息记录
                    l_task = result['tasks'][0]
                    # 更新执行结果
                    if not job:
                        # 更新为下次不再需要更新，因为job中已经移除
                        task.is_get_last = '01'

                    task.last_exec_time = '{0}|{1}'.format(l_task.get('start_time'), task_states.get(l_task.get('status', 'running')))
                    task.save()
            except Exception, e:
                logger.error("get_task_info_erro [%s]\n[%s]" % (task.task_uuid, e.message))
        logger.info("end get task exec info <<<<<<")
    except:
        logger.error("get task exec info error\n [%s]" % ( traceback.format_exc() ))


if __name__ == '__main__':
    get_task_exec_info()
