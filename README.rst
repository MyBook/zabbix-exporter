zabbix_exporter
===============

.. image:: https://travis-ci.org/Eksmo/zabbix-exporter.svg?branch=master
   :target: https://travis-ci.org/Eksmo/zabbix-exporter

.. image:: https://codecov.io/gh/Eksmo/zabbix-exporter/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/Eksmo/zabbix-exporter

Usage
=====
::

    Usage: zabbix_exporter [OPTIONS]

      Zabbix metrics exporter for Prometheus

      Use config file to map zabbix metrics names/labels into prometheus. Config
      below transfroms this:

          local.metric[uwsgi,workers,myapp,busy] = 8
          local.metric[uwsgi,workers,myapp,idle] = 6

      into familiar Prometheus gauges:

          uwsgi_workers{instance="host1",app="myapp",status="busy"} 8
          uwsgi_workers{instance="host1",app="myapp",status="idle"} 6

      YAML:

          metrics:
            - key: 'local.metric[uwsgi,workers,*,*]'
              name: 'uwsgi_workers'
              labels:
                app: $1
                status: $2
              reject:
                - 'total'

    Options:
      --config PATH               Path to exporter config
      --port INTEGER              Port to serve prometheus stats [default: 9224]
      --url TEXT                  HTTP URL for zabbix instance
      --login TEXT                Zabbix username
      --password TEXT             Zabbix password
      --verify-tls / --no-verify  Enable TLS cert verification [default: true]
      --timeout INTEGER           API read/connect timeout
      --verbose
      --dump-metrics              Output all metrics for human to write yaml
                                  config
      --version
      --help                      Show this message and exit.
