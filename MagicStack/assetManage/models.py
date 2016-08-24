# coding: utf-8

import datetime
from django.db import models
from userManage.models import User, UserGroup
from proxyManage.models import Proxy

ASSET_ENV = (
    (1, U'生产环境'),
    (2, U'测试环境')
    )

ASSET_STATUS = (
    (1, u"已使用"),
    (2, u"未使用"),
    (3, u"报废")
    )

ASSET_TYPE = (
    (1, u"物理机"),
    (2, u"虚拟机"),
    (3, u"交换机"),
    (4, u"路由器"),
    (5, u"防火墙"),
    (6, u"Docker"),
    (7, u"其他")
    )


class AssetGroup(models.Model):
    GROUP_TYPE = (
        ('P', 'PRIVATE'),
        ('A', 'ASSET'),
    )
    name = models.CharField(max_length=80, unique=True)
    comment = models.CharField(max_length=160, blank=True)

    def __unicode__(self):
        return self.name


class IDC(models.Model):
    name = models.CharField(max_length=32, verbose_name=u'机房名称')
    bandwidth = models.CharField(max_length=32, blank=True, default='', verbose_name=u'机房带宽')
    linkman = models.CharField(max_length=16, blank=True,  default='', verbose_name=u'联系人')
    phone = models.CharField(max_length=32, blank=True, default='', verbose_name=u'联系电话')
    address = models.CharField(max_length=128, blank=True, default='', verbose_name=u"机房地址")
    network = models.TextField(blank=True, default='', verbose_name=u"IP地址段")
    date_added = models.DateField(auto_now=True, null=True)
    operator = models.CharField(max_length=32, blank=True, default='', verbose_name=u"运营商")
    comment = models.CharField(max_length=128, blank=True, default='', verbose_name=u"备注")

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u"IDC机房"
        verbose_name_plural = verbose_name


class NetWorking(models.Model):
    net_name = models.CharField(max_length=90, verbose_name=u'添加网卡')
    mac_address = models.CharField(max_length=90, verbose_name=u'MAC地址')
    mtu = models.CharField(max_length=90, blank=True, null=True, verbose_name=u'最大传输单元')
    ip_address = models.CharField(max_length=90, verbose_name=u'IP地址')
    static = models.BooleanField(default=True, verbose_name='Static')
    subnet_mask = models.CharField(max_length=90, blank=True, default='', verbose_name=u'子网掩码')
    per_gateway = models.CharField(max_length=90, blank=True, default='', verbose_name=u'默认网关')
    dns_name = models.CharField(max_length=90, blank=True, default='', verbose_name=u'DNS名称')
    static_routes = models.CharField(max_length=100, blank=True, default='', verbose_name=u'静态路由')
    active = models.BooleanField(default=1, help_text=u'网卡状态')
    device = models.CharField(max_length=100, default='', help_text=u'网卡名字')
    macaddress = models.CharField(max_length=100, default='', help_text=u'从ansible中获取的MAC地址')
    module = models.CharField(max_length=100, default='', help_text=u'网卡驱动')
    pciid = models.CharField(max_length=100, default='')
    promisc = models.BooleanField(default=1)
    type = models.CharField(max_length=60, default='', help_text=u'网卡类型')

    def __unicode__(self):
        return self.net_name


class NetWorkingGlobal(models.Model):
    hostname = models.CharField(max_length=90, verbose_name=u'主机名')
    gateway = models.CharField(max_length=90, verbose_name=u'网关')
    name_servers = models.CharField(max_length=90, blank=True, default='', verbose_name=u'域名服务器')

    def __unicode__(self):
        return self.hostname


class PowerManage(models.Model):
    POWER_TYPE = (
                    ('drac5', 'drac5'),
                    ('idrac', 'idrac'),
                    ('ilo', 'ilo'),
                    ('ilo2', 'ilo2'),
                    ('ilo3', 'ilo3'),
                    ('ilo4', 'ilo4'),
                    ('intelmodular', 'intelmodular'),
                    ('ipmilan', 'ipmilan'),
    )

    power_type = models.CharField(choices=POWER_TYPE, max_length=90, default='ipmilan', verbose_name=u'电源管理类型')
    power_address = models.CharField(max_length=90, verbose_name=u'电源管理地址')
    power_username = models.CharField(max_length=90, verbose_name=u'电源管理用户名')
    power_password = models.CharField(max_length=90, verbose_name=u'电源管理用户密码')

    def __unicode__(self):
        return self.power_address


class Asset(models.Model):
    STATUS_TYPE = (
        ('1', 'producton'),
        ('2', 'development'),
        ('3', 'testing'),
        ('4', 'acceptance'),
    )

    id_unique = models.CharField(max_length=200, blank=True, unique=True, verbose_name=u"唯一标示")
    ip = models.CharField(max_length=32, blank=True, default='', verbose_name=u"主机IP")
    other_ip = models.CharField(max_length=255, blank=True, default='', verbose_name=u"其他IP")
    name = models.CharField(max_length=100, blank=True, unique=True, verbose_name=u'名字')
    profile = models.CharField(max_length=100, blank=True,  verbose_name=u'用户配置文件')
    status = models.CharField(choices=STATUS_TYPE, max_length=90, default='1', verbose_name=u'状态')
    kickstart = models.CharField(max_length=255, default='', verbose_name=u'创建元数据')
    netboot_enabled = models.BooleanField(default=True, verbose_name=u'网络引导')
    port = models.IntegerField(blank=True, null=True, verbose_name=u"端口号")
    group = models.ManyToManyField(AssetGroup, blank=True, verbose_name=u"所属主机组")
    username = models.CharField(max_length=16, blank=True, default='', verbose_name=u"管理用户名")
    password = models.CharField(max_length=64, blank=True, default='', verbose_name=u"密码")
    idc = models.ForeignKey(IDC, blank=True, null=True,  on_delete=models.SET_NULL, verbose_name=u'机房')
    product_name = models.CharField(max_length=64, blank=True, default='', verbose_name=u'硬件厂商型号')
    cpu = models.CharField(max_length=64, blank=True, default='', verbose_name=u'CPU')
    memory = models.CharField(max_length=128, blank=True, default='', verbose_name=u'内存')
    disk = models.CharField(max_length=1024, blank=True, default='', verbose_name=u'硬盘')
    system_type = models.CharField(max_length=32, blank=True, default='', verbose_name=u"系统类型")
    system_version = models.CharField(max_length=8, blank=True, default='', verbose_name=u"系统版本号")
    system_arch = models.CharField(max_length=16, blank=True, default='', verbose_name=u"系统平台")
    cabinet = models.CharField(max_length=32, blank=True, default='', verbose_name=u'机柜号')
    position = models.IntegerField(blank=True, null=True, verbose_name=u'机器位置')
    number = models.CharField(max_length=32, blank=True, default='', verbose_name=u'资产编号')
    machine_status = models.IntegerField(choices=ASSET_STATUS, blank=True, null=True, default=1, verbose_name=u"机器状态")
    asset_type = models.IntegerField(choices=ASSET_TYPE, blank=True, null=True, default=1, verbose_name=u"主机类型")
    product_serial = models.CharField(max_length=128, blank=True, default='', verbose_name=u"SN编号")
    proxy = models.ForeignKey(Proxy, verbose_name=u'所属代理')
    networking_g = models.ForeignKey(NetWorkingGlobal,  verbose_name=u'全局网络设置')
    networking = models.ManyToManyField(NetWorking,  verbose_name=u'网络')
    power_manage = models.ForeignKey(PowerManage, verbose_name=u'电源管理')
    date_added = models.DateTimeField(auto_now=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name=u"是否激活")
    comment = models.CharField(max_length=128, blank=True, default='', verbose_name=u"备注")
    devices = models.TextField(default='', help_text=u'设备信息')
    bios_date = models.CharField(max_length=100, default='')
    bios_version = models.CharField(max_length=100, default='')
    product_uuid = models.CharField(max_length=100, default='')
    product_version = models.CharField(max_length=100, default='')
    system_vendor = models.CharField(max_length=100, default='')

    def __unicode__(self):
        return self.name


class AssetRecord(models.Model):
    asset = models.ForeignKey(Asset)
    username = models.CharField(max_length=30, null=True)
    alert_time = models.DateTimeField(auto_now_add=True, null=True)
    content = models.TextField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)



