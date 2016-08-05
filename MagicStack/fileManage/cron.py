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
import traceback
import urllib2
import re

from common.interface import APIRequest
from MagicStack.api import *

from models import File


def get_result_from_proxy(file):
    # 调用proxy接口
    api = APIRequest('{0}/v1.0/job_task/{1}?limit=1'.format(file.proxy.url, file.task_uuid),
                     file.proxy.username,
                     CRYPTOR.decrypt(file.proxy.password))
    result, code = api.req_get()
    if code != 200:
        # 获取失败，下次继续获取
        result = {}
    else:
        result = result['result']
    return result


def get_file_upload_info():
    """
        更新任务，最后执行记录
    """
    task_states = {
        'complete': '完成',
        'failed': '失败',
        'running': '执行中'
    }
    try:
        logger.info("start get file upload info >>>>>>")
        files = File.objects.filter(status='00')
        pattern = re.compile(
            r'(?P<ip>\d{0,3}\.\d{0,3}\.\d{0,3}\.\d{0,3}).*?(?P<result>SUCCESS|FAILED|SKIPPED|UNREACHABLE).*?')
        for file in files:
            try:
                logger.info("handler file upload {%s}" % file.task_uuid)
                result = get_result_from_proxy(file)
                if result:
                    job = result['job']
                    # 最后执行消息记录
                    last_task = result['tasks'][0]
                    if last_task.get('status') != 'running':
                        # 确定是完成之后，再进行content的获取
                        file.status = '01'
                        # url = '{0}/v1.0/job_task_replay/{1}'.format(file.proxy.url, file.task_uuid)
                        content = json.loads(last_task.get('result'))
                        result = sorted(content.items(), key=lambda x: x[0])
                        res = ""

                        for t, line in result:
                            # 筛选符合的字符串
                            match = pattern.search(line)
                            if match:
                                res += match.group()
                                res += "<br>"
                        file.result = res
                        file.save()
            except Exception, e:
                logger.error("handler file upload erro [%s]" % (file.task_uuid))
                logger.error(traceback.format_exc())
        logger.info("end get file upload info <<<<<<")

    except:
        logger.error("get file upload info error\n [%s]" % ( traceback.format_exc() ))


if __name__ == '__main__':
    get_file_upload_info()
