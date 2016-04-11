zabbix_exporter
===============

::

Usage: zabbix_exporter [OPTIONS]

  Zabbix metrics exporter for Prometheus

Options:
  --config PATH               Path to exporter config [required]
  --port INTEGER              Port to serve prometheus stats [default: 9224]
  --url TEXT                  HTTP URL for zabbix instance
  --login TEXT                Zabbix username
  --password TEXT             Zabbix password
  --verify-tls / --no-verify  Enable TLS cert verification [default: true]
  --timeout INTEGER           API read/connect timeout
  --verbose
  --version
  --help                      Show this message and exit.
