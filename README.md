# Zabbix Exporter

This project is a fork of [original zabbix exporter](https://github.com/MyBook/zabbix-exporter) 
with advances functionality: 
filtering was added for each zabbix metric with configuration-defined hosts and item names, which significantly 
improves execution time.

### Usage example
```shell
Usage: zabbix_exporter [OPTIONS]
  Zabbix metrics exporter for Prometheus

  Use config file to map zabbix metrics names/labels into prometheus. Config
  below transforms this:
      local.metric[uwsgi,workers,myapp,busy] = 8
      local.metric[uwsgi,workers,myapp,idle] = 6

  into familiar Prometheus gauges:
      uwsgi_workers{instance="host1",app="myapp",status="busy"} 8
      uwsgi_workers{instance="host1",app="myapp",status="idle"} 6

  YAML config example:
      metrics:
        - key: 'local.metric[uwsgi,workers,*,*]'
          name: 'uwsgi_workers'
          labels:
            app: $1
            status: $2
          reject:
            - 'total'
          hosts:
            - name.of.host.1
            - name.of.host.2
          item_names:
            - '*item.name.substr.1*'
            - '*item.name.substr.2*'

Options:
  --config PATH               Path to exporter config
  --port INTEGER              Port to serve prometheus stats [default: 9224]
  --url TEXT                  HTTP URL for zabbix instance
  --login TEXT                Zabbix username
  --password TEXT             Zabbix password
  --verify-tls / --no-verify  Enable TLS cert verification [default: true]
  --timeout INTEGER           API read/connect timeout
  --verbose
  --help                      Show this message and exit.

```    

### Deploying with Docker
```shell
docker run -d --name zabbix_exporter -v /path/to/your/config.yml:/zabbix_exporter/zabbix_exporter.yml --env=ZABBIX_URL="https://zabbix.example.com/" --env="ZABBIX_LOGIN=username" --env="ZABBIX_PASSWORD=secret" mybook/zabbix-exporter
```