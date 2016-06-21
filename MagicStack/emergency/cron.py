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
import datetime
from emergency.models import EmergencyEvent
from emer_api import send_email, send_wx_mail
from MagicStack.api import logger


def get_emergency_event():
    """
    告警事件
    """
    current_time = datetime.datetime.now()
    filtet_time = datetime.datetime(current_time.year, current_time.month, current_time.day)
    emergency_events = EmergencyEvent.objects.filter(emer_time__gt=filtet_time).filter(emer_result=0)  # 获取当天未执行的事件
    for item in emergency_events:
        emer_rules = item.emer_event
        rules_status = emer_rules.status

        if not item.emer_info:
            continue

        email_msg = item.emer_info
        # 获取告警事件中已启用的告警规则,若告警规则未启用则不告警
        if rules_status == 1:
            rules_time = emer_rules.emergency_time
            rules_user = emer_rules.staff.all()
            rules_media_type = emer_rules.media_type.type
            # 判断时间是全部时间还是工作日,或者周末 1：全部时间 2：工作日 3：周末
            if rules_time == 1:
                try:
                    # 判断告警类型 "0":电子邮件  "1": 微信
                    if rules_media_type == "0":
                        send_email_users = [user.email for user in rules_user]
                        send_email(emer_rules.media_type, u"告警信息", send_email_users, email_msg)
                        item.emer_result = 1
                        item.save()
                    else:
                        send_wx_users = []
                except Exception as e:
                    logger.error(e)
            elif rules_time == 2:
                print "工作日"
                is_weekday = datetime.datetime.today().weekday()
                if 0 <= is_weekday and is_weekday <= 4:
                    try:
                        if rules_media_type == "0":
                            send_email_users = [user.email for user in rules_user]
                            send_email(emer_rules.media_type, u"告警信息", send_email_users, email_msg)
                            item.emer_result = 1
                            item.save()
                        else:
                            send_wx_users = []
                    except Exception as e:
                        logger.error(e)
            else:
                print "周末"
                is_weekend = datetime.datetime.today().weekday()
                if is_weekend == 5 or is_weekend == 6:
                    try:
                        if rules_media_type == "0":
                            send_email_users = [user.email for user in rules_user]
                            send_email(emer_rules.media_type, u"告警信息", send_email_users, email_msg)
                            item.emer_result = 1
                            item.save()
                        else:
                            send_wx_users = []
                    except Exception as e:
                        logger.error(e)

