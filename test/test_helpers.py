from dockerenforcer.config import Config
from dockerenforcer.docker_helper import Container, CheckSource
from dockerenforcer.killer import Judge


class RulesTestHelper:
    def __init__(self, rules, config=Config(), container_count=1, mem_limit=0, cpu_share=0, cpu_period=0, cpu_quota=0,
                 mem_usage=0):
        self.judge = Judge(rules, "container", config)
        cid = '7de82a4e90f1bd4fd022bcce298e7277b8aec009e222892e44769d6c636b8205'
        params = {'Image': 'sha256:47bcc53f74dc94b1920f0b34f6036096526296767650f223433fe65c35f149eb',
                  'HostConfig': {'Isolation': '', 'IOMaximumBandwidth': 0, 'CpuPercent': 0, 'ReadonlyRootfs': False,
                                 'CpuQuota': cpu_quota, 'IpcMode': '', 'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0},
                                 'BlkioDeviceWriteIOps': None, 'PidMode': '', 'BlkioDeviceWriteBps': None,
                                 'PortBindings': {'8080/tcp': [{'HostIp': '', 'HostPort': '8080'}]},
                                 'BlkioDeviceReadIOps': None, 'ContainerIDFile': '', 'ConsoleSize': [0, 0],
                                 'IOMaximumIOps': 0, 'ShmSize': 67108864, 'GroupAdd': None, 'Cgroup': '',
                                 'DiskQuota': 0, 'DnsSearch': [], 'BlkioWeight': 0, 'Dns': [], 'OomKillDisable': False,
                                 'CpuPeriod': cpu_period, 'DnsOptions': [], 'NetworkMode': 'default', 'CpuCount': 0,
                                 'KernelMemory': 0, 'Links': None, 'Memory': mem_limit, 'VolumesFrom': None,
                                 'MemorySwap': -1, 'Ulimits': None, 'UsernsMode': '', 'Devices': [], 'CpusetMems': '',
                                 'MemorySwappiness': -1, 'Privileged': False, 'CpuShares': cpu_share, 'CpusetCpus': '',
                                 'VolumeDriver': '', 'SecurityOpt': None, 'OomScoreAdj': 0, 'PublishAllPorts': False,
                                 'AutoRemove': False, 'MemoryReservation': 0, 'BlkioDeviceReadBps': None,
                                 'PidsLimit': 0, 'Runtime': 'runc', 'UTSMode': '', 'Binds': ['/:/tmp'], 'CapDrop': None,
                                 'ExtraHosts': None, 'BlkioWeightDevice': None,
                                 'LogConfig': {'Type': 'json-file', 'Config': {}}, 'CgroupParent': '', 'CapAdd': None},
                  'MountLabel': '', 'AppArmorProfile': '', 'Driver': 'aufs',
                  'ResolvConfPath': '/opt/docker/containers/7de82a4e90f1bd4fd022bcce298e7277b8aec009e222892e44769d6c636b8205/resolv.conf',
                  'ExecIDs': None, 'Created': '2016-10-27T19:30:04.433919486Z', 'Path': 'sleep',
                  'Id': '7de82a4e90f1bd4fd022bcce298e7277b8aec009e222892e44769d6c636b8205',
                  'State': {'StartedAt': '2016-10-27T19:30:04.770734821Z', 'Status': 'running', 'ExitCode': 0,
                            'OOMKilled': False, 'Dead': False, 'FinishedAt': '0001-01-01T00:00:00Z', 'Pid': 25800,
                            'Error': '', 'Paused': False, 'Running': True, 'Restarting': False},
                  'Mounts': [{'Destination': '/tmp', 'Source': '/', 'Mode': '', 'RW': True, 'Propagation': 'rprivate'}],
                  'HostsPath': '/opt/docker/containers/7de82a4e90f1bd4fd022bcce298e7277b8aec009e222892e44769d6c636b8205/hosts',
                  'ProcessLabel': '', 'GraphDriver': {'Data': None, 'Name': 'aufs'},
                  'LogPath': '/opt/docker/containers/7de82a4e90f1bd4fd022bcce298e7277b8aec009e222892e44769d6c636b8205/7de82a4e90f1bd4fd022bcce298e7277b8aec009e222892e44769d6c636b8205-json.log',
                  'Name': '/testing_vro',
                  'Config': {'OpenStdin': True, 'Image': 'busybox', 'ExposedPorts': {'8080/tcp': {}},
                             'Cmd': ['sleep', '1000'], 'Hostname': '7de82a4e90f1', 'Volumes': None, 'Labels': {},
                             'Tty': True, 'Env': None, 'Domainname': '', 'OnBuild': None, 'StdinOnce': True, 'User': '',
                             'AttachStdin': True, 'AttachStderr': True, 'AttachStdout': True, 'Entrypoint': None,
                             'WorkingDir': ''},
                  'NetworkSettings': {'GlobalIPv6PrefixLen': 0, 'SecondaryIPv6Addresses': None, 'GlobalIPv6Address': '',
                                      'SandboxID': '2df12d715799cfdd03f2f421ea64b19b05ec60ff14ae86a29723e0c1b3199d47',
                                      'Bridge': '',
                                      'EndpointID': 'a5d310ae48dc6b7f70754ff94a0f242507472bbcc3dfd81a5a3da319e19695ef',
                                      'SandboxKey': '/var/run/docker/netns/2df12d715799', 'SecondaryIPAddresses': None,
                                      'Networks': {
                                          'bridge': {'GlobalIPv6PrefixLen': 0, 'GlobalIPv6Address': '', 'Links': None,
                                                     'IPPrefixLen': 16,
                                                     'EndpointID': 'a5d310ae48dc6b7f70754ff94a0f242507472bbcc3dfd81a5a3da319e19695ef',
                                                     'IPAddress': '172.17.0.2', 'Gateway': '172.17.0.1',
                                                     'Aliases': None, 'MacAddress': '02:42:ac:11:00:02',
                                                     'IPAMConfig': None, 'IPv6Gateway': '',
                                                     'NetworkID': 'd5ce26d62a33223deca40e3d99232557205af38093bbd23922cf6f1ed5c9cf56'}},
                                      'MacAddress': '02:42:ac:11:00:02',
                                      'Ports': {'8080/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]},
                                      'IPv6Gateway': '', 'IPPrefixLen': 16, 'LinkLocalIPv6PrefixLen': 0,
                                      'HairpinMode': False, 'IPAddress': '172.17.0.2', 'LinkLocalIPv6Address': '',
                                      'Gateway': '172.17.0.1'}, 'Args': ['1000'],
                  'HostnamePath': '/opt/docker/containers/7de82a4e90f1bd4fd022bcce298e7277b8aec009e222892e44769d6c636b8205/hostname',
                  'RestartCount': 0}
        metrics = {'blkio_stats': {'io_wait_time_recursive': [], 'io_serviced_recursive': [], 'io_merged_recursive': [],
                                   'io_queue_recursive': [], 'io_service_time_recursive': [], 'sectors_recursive': [],
                                   'io_time_recursive': [], 'io_service_bytes_recursive': []},
                   'memory_stats': {'limit': 536870912, 'usage': mem_usage,
                                    'stats': {'total_active_file': 0, 'pgfault': 318,
                                              'hierarchical_memory_limit': 536870912, 'total_pgfault': 318,
                                              'mapped_file': 0, 'total_rss': 32768, 'pgmajfault': 0,
                                              'total_active_anon': 32768, 'inactive_anon': 0, 'rss': 32768,
                                              'inactive_file': 0, 'active_anon': 32768, 'total_pgpgin': 293,
                                              'active_file': 0, 'unevictable': 0, 'pgpgout': 285, 'total_pgpgout': 285,
                                              'cache': 0, 'total_dirty': 0, 'total_writeback': 0,
                                              'total_mapped_file': 0, 'total_inactive_file': 0, 'writeback': 0,
                                              'rss_huge': 0, 'dirty': 0, 'pgpgin': 293, 'total_inactive_anon': 0,
                                              'total_rss_huge': 0, 'total_pgmajfault': 0, 'total_unevictable': 0,
                                              'total_cache': 0}, 'max_usage': 1581056, 'failcnt': 0},
                   'pids_stats': {'current': 1},
                   'cpu_stats': {'throttling_data': {'throttled_time': 0, 'throttled_periods': 0, 'periods': 0},
                                 'system_cpu_usage': 374267840000000,
                                 'cpu_usage': {'total_usage': 29623824, 'usage_in_usermode': 20000000,
                                               'usage_in_kernelmode': 0,
                                               'percpu_usage': [773217, 129812, 355729, 204383, 24629686, 493977,
                                                                520620, 2516400]}},
                   'precpu_stats': {'throttling_data': {'throttled_time': 0, 'throttled_periods': 0, 'periods': 0},
                                    'system_cpu_usage': 374259930000000,
                                    'cpu_usage': {'total_usage': 29623824, 'usage_in_usermode': 20000000,
                                                  'usage_in_kernelmode': 0,
                                                  'percpu_usage': [773217, 129812, 355729, 204383, 24629686, 493977,
                                                                   520620, 2516400]}}, 'networks': {
                'eth0': {'rx_dropped': 0, 'tx_packets': 7, 'rx_bytes': 8719, 'tx_dropped': 0, 'rx_errors': 0,
                         'tx_bytes': 578, 'rx_packets': 80, 'tx_errors': 0}}, 'read': '2016-10-27T19:30:13.751688232Z'}
        self.containers = []
        for cnt in range(container_count):
            self.containers.append(Container(cid, params, metrics, cnt, check_source=CheckSource.Event))

    def get_verdicts(self):
        return list(map(lambda c: self.judge.should_be_killed(c), self.containers))


class ApiTestHelper:
    # docker run -it alpine sh
    authz_req_plain_run = b'{"RequestMethod":"POST","RequestUri":"/v1.30/containers/create","RequestBody":"eyJIb3N0bmFtZSI6IiIsIkRvbWFpbm5hbWUiOiIiLCJVc2VyIjoiIiwiQXR0YWNoU3RkaW4iOnRydWUsIkF0dGFjaFN0ZG91dCI6dHJ1ZSwiQXR0YWNoU3RkZXJyIjp0cnVlLCJUdHkiOnRydWUsIk9wZW5TdGRpbiI6dHJ1ZSwiU3RkaW5PbmNlIjp0cnVlLCJFbnYiOltdLCJDbWQiOlsic2giXSwiSW1hZ2UiOiJhbHBpbmUiLCJWb2x1bWVzIjp7fSwiV29ya2luZ0RpciI6IiIsIkVudHJ5cG9pbnQiOm51bGwsIk9uQnVpbGQiOm51bGwsIkxhYmVscyI6e30sIkhvc3RDb25maWciOnsiQmluZHMiOm51bGwsIkNvbnRhaW5lcklERmlsZSI6IiIsIkxvZ0NvbmZpZyI6eyJUeXBlIjoiIiwiQ29uZmlnIjp7fX0sIk5ldHdvcmtNb2RlIjoiZGVmYXVsdCIsIlBvcnRCaW5kaW5ncyI6e30sIlJlc3RhcnRQb2xpY3kiOnsiTmFtZSI6Im5vIiwiTWF4aW11bVJldHJ5Q291bnQiOjB9LCJBdXRvUmVtb3ZlIjpmYWxzZSwiVm9sdW1lRHJpdmVyIjoiIiwiVm9sdW1lc0Zyb20iOm51bGwsIkNhcEFkZCI6bnVsbCwiQ2FwRHJvcCI6bnVsbCwiRG5zIjpbXSwiRG5zT3B0aW9ucyI6W10sIkRuc1NlYXJjaCI6W10sIkV4dHJhSG9zdHMiOm51bGwsIkdyb3VwQWRkIjpudWxsLCJJcGNNb2RlIjoiIiwiQ2dyb3VwIjoiIiwiTGlua3MiOm51bGwsIk9vbVNjb3JlQWRqIjowLCJQaWRNb2RlIjoiIiwiUHJpdmlsZWdlZCI6ZmFsc2UsIlB1Ymxpc2hBbGxQb3J0cyI6ZmFsc2UsIlJlYWRvbmx5Um9vdGZzIjpmYWxzZSwiU2VjdXJpdHlPcHQiOm51bGwsIlVUU01vZGUiOiIiLCJVc2VybnNNb2RlIjoiIiwiU2htU2l6ZSI6MCwiQ29uc29sZVNpemUiOlswLDBdLCJJc29sYXRpb24iOiIiLCJDcHVTaGFyZXMiOjAsIk1lbW9yeSI6MCwiTmFub0NwdXMiOjAsIkNncm91cFBhcmVudCI6IiIsIkJsa2lvV2VpZ2h0IjowLCJCbGtpb1dlaWdodERldmljZSI6bnVsbCwiQmxraW9EZXZpY2VSZWFkQnBzIjpudWxsLCJCbGtpb0RldmljZVdyaXRlQnBzIjpudWxsLCJCbGtpb0RldmljZVJlYWRJT3BzIjpudWxsLCJCbGtpb0RldmljZVdyaXRlSU9wcyI6bnVsbCwiQ3B1UGVyaW9kIjowLCJDcHVRdW90YSI6MCwiQ3B1UmVhbHRpbWVQZXJpb2QiOjAsIkNwdVJlYWx0aW1lUnVudGltZSI6MCwiQ3B1c2V0Q3B1cyI6IiIsIkNwdXNldE1lbXMiOiIiLCJEZXZpY2VzIjpbXSwiRGV2aWNlQ2dyb3VwUnVsZXMiOm51bGwsIkRpc2tRdW90YSI6MCwiS2VybmVsTWVtb3J5IjowLCJNZW1vcnlSZXNlcnZhdGlvbiI6MCwiTWVtb3J5U3dhcCI6MCwiTWVtb3J5U3dhcHBpbmVzcyI6LTEsIk9vbUtpbGxEaXNhYmxlIjpmYWxzZSwiUGlkc0xpbWl0IjowLCJVbGltaXRzIjpudWxsLCJDcHVDb3VudCI6MCwiQ3B1UGVyY2VudCI6MCwiSU9NYXhpbXVtSU9wcyI6MCwiSU9NYXhpbXVtQmFuZHdpZHRoIjowfSwiTmV0d29ya2luZ0NvbmZpZyI6eyJFbmRwb2ludHNDb25maWciOnt9fX0K","RequestHeaders":{"Content-Length":"1425","Content-Type":"application/json","User-Agent":"Docker-Client/17.06.0-ce (linux)"}}\n'
    # docker run -m 1024m -it alpine sh
    authz_req_plain_run_mem_limit = b'{"RequestMethod":"POST","RequestUri":"/v1.30/containers/create","RequestBody":"eyJIb3N0bmFtZSI6IiIsIkRvbWFpbm5hbWUiOiIiLCJVc2VyIjoiIiwiQXR0YWNoU3RkaW4iOnRydWUsIkF0dGFjaFN0ZG91dCI6dHJ1ZSwiQXR0YWNoU3RkZXJyIjp0cnVlLCJUdHkiOnRydWUsIk9wZW5TdGRpbiI6dHJ1ZSwiU3RkaW5PbmNlIjp0cnVlLCJFbnYiOltdLCJDbWQiOlsic2giXSwiSW1hZ2UiOiJhbHBpbmUiLCJWb2x1bWVzIjp7fSwiV29ya2luZ0RpciI6IiIsIkVudHJ5cG9pbnQiOm51bGwsIk9uQnVpbGQiOm51bGwsIkxhYmVscyI6e30sIkhvc3RDb25maWciOnsiQmluZHMiOm51bGwsIkNvbnRhaW5lcklERmlsZSI6IiIsIkxvZ0NvbmZpZyI6eyJUeXBlIjoiIiwiQ29uZmlnIjp7fX0sIk5ldHdvcmtNb2RlIjoiZGVmYXVsdCIsIlBvcnRCaW5kaW5ncyI6e30sIlJlc3RhcnRQb2xpY3kiOnsiTmFtZSI6Im5vIiwiTWF4aW11bVJldHJ5Q291bnQiOjB9LCJBdXRvUmVtb3ZlIjpmYWxzZSwiVm9sdW1lRHJpdmVyIjoiIiwiVm9sdW1lc0Zyb20iOm51bGwsIkNhcEFkZCI6bnVsbCwiQ2FwRHJvcCI6bnVsbCwiRG5zIjpbXSwiRG5zT3B0aW9ucyI6W10sIkRuc1NlYXJjaCI6W10sIkV4dHJhSG9zdHMiOm51bGwsIkdyb3VwQWRkIjpudWxsLCJJcGNNb2RlIjoiIiwiQ2dyb3VwIjoiIiwiTGlua3MiOm51bGwsIk9vbVNjb3JlQWRqIjowLCJQaWRNb2RlIjoiIiwiUHJpdmlsZWdlZCI6ZmFsc2UsIlB1Ymxpc2hBbGxQb3J0cyI6ZmFsc2UsIlJlYWRvbmx5Um9vdGZzIjpmYWxzZSwiU2VjdXJpdHlPcHQiOm51bGwsIlVUU01vZGUiOiIiLCJVc2VybnNNb2RlIjoiIiwiU2htU2l6ZSI6MCwiQ29uc29sZVNpemUiOlswLDBdLCJJc29sYXRpb24iOiIiLCJDcHVTaGFyZXMiOjAsIk1lbW9yeSI6MTA3Mzc0MTgyNCwiTmFub0NwdXMiOjAsIkNncm91cFBhcmVudCI6IiIsIkJsa2lvV2VpZ2h0IjowLCJCbGtpb1dlaWdodERldmljZSI6bnVsbCwiQmxraW9EZXZpY2VSZWFkQnBzIjpudWxsLCJCbGtpb0RldmljZVdyaXRlQnBzIjpudWxsLCJCbGtpb0RldmljZVJlYWRJT3BzIjpudWxsLCJCbGtpb0RldmljZVdyaXRlSU9wcyI6bnVsbCwiQ3B1UGVyaW9kIjowLCJDcHVRdW90YSI6MCwiQ3B1UmVhbHRpbWVQZXJpb2QiOjAsIkNwdVJlYWx0aW1lUnVudGltZSI6MCwiQ3B1c2V0Q3B1cyI6IiIsIkNwdXNldE1lbXMiOiIiLCJEZXZpY2VzIjpbXSwiRGV2aWNlQ2dyb3VwUnVsZXMiOm51bGwsIkRpc2tRdW90YSI6MCwiS2VybmVsTWVtb3J5IjowLCJNZW1vcnlSZXNlcnZhdGlvbiI6MCwiTWVtb3J5U3dhcCI6MCwiTWVtb3J5U3dhcHBpbmVzcyI6LTEsIk9vbUtpbGxEaXNhYmxlIjpmYWxzZSwiUGlkc0xpbWl0IjowLCJVbGltaXRzIjpudWxsLCJDcHVDb3VudCI6MCwiQ3B1UGVyY2VudCI6MCwiSU9NYXhpbXVtSU9wcyI6MCwiSU9NYXhpbXVtQmFuZHdpZHRoIjowfSwiTmV0d29ya2luZ0NvbmZpZyI6eyJFbmRwb2ludHNDb25maWciOnt9fX0K","RequestHeaders":{"Content-Length":"1434","Content-Type":"application/json","User-Agent":"Docker-Client/17.06.0-ce (linux)"}}\n'
    # docker cp test:/tmp/1 /tmp
    authz_req_copy_from_cont = b'{"RequestMethod":"GET","RequestUri":"/v1.30/containers/test/archive?path=%2Ftmp%2F1","RequestHeaders":{"User-Agent":"Docker-Client/17.06.0-ce (linux)"}}\n'
    # docker cp /tmp/1 test:/tmp/
    authz_req_copy_to_cont = b'{"RequestMethod":"HEAD","RequestUri":"/v1.30/containers/test/archive?path=%2Ftmp%2F","RequestHeaders":{"User-Agent":"Docker-Client/17.06.0-ce (linux)"}}\n'