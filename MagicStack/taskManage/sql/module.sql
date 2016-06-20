insert into taskManage_module(task_type, group_name, module_name, module_statu, module_validation, comment)
values( 'ansible', 'system', 'ping', '00', '', 'Ansible ping模块，用于测试连接' );
insert into taskManage_module(task_type, group_name, module_name, module_statu, module_validation, comment)
values( 'ansible', 'system', 'mount', '00', '', 'Ansible mount，进行系统挂载' );
insert into taskManage_module(task_type, group_name, module_name, module_statu, module_validation, comment)
values( 'ansible', 'commands', 'shell', '00', '', 'Ansible shell模块，输入linux shell命令执行' );
insert into taskManage_module(task_type, group_name, module_name, module_statu, module_validation, comment)
values( 'ansible', 'commands', 'command', '00', '', 'Ansible command模块，输入linux command命令执行' );
insert into taskManage_module(task_type, group_name, module_name, module_statu, module_validation, comment)
values( 'ansible', 'commands', 'script', '00', '', 'Ansible script模块，输入linux command命令执行' );
insert into taskManage_module(task_type, group_name, module_name, module_statu, module_validation, comment)
values( 'ansible', 'commands', 'raw', '00', '', 'Ansible raw模块，输入linux command命令执行' );
insert into taskManage_module(task_type, group_name, module_name, module_statu, module_validation, comment)
values( 'other', 'other', 'other', '00', '', 'Other test' );