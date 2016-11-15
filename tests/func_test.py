# coding: utf-8

import pytest
import requests

from zabbix_exporter.prometheus import text_string_to_metric_families


@pytest.mark.parametrize("config_name,timestamps", [
    ("disable_timestamps", (None, None, None, None, None)),
    ("explicit_config", (1460359130, 1460359130, 1460359143, 1460359143, 1460359140)),
])
def test_configs(zabbixserver, zabbix_exporter_cli, config_name, timestamps):
    args = ['--url', zabbixserver.url,
            '--no-verify', '--config', 'tests/configs/%s.yaml' % config_name,
            '--login', 'demo', '--password', 'demo', '--port', '9224', '--verbose']
    zabbix_exporter_cli(args)

    response = requests.get('http://localhost:9224/metrics/')
    metrics = [m for m in text_string_to_metric_families(response.text)
               if not m.name.startswith('zabbix_exporter_') and not m.name.startswith('process_')]

    assert len(metrics) == 4
    assert metrics[0].name == 'redis_connected_clients'
    assert metrics[0].type == 'untyped'
    assert metrics[0].samples == [
        (u'redis_connected_clients',
         {u'port': u'6380',
          u'instance': u'rough-snowflake-web'},
         10.0, timestamps[0])]

    assert metrics[1].name == 'uwsgi_rss'
    assert metrics[1].documentation == 'UWSGI RSS sum'
    assert metrics[1].type == 'untyped'
    assert metrics[1].samples == [
        (u'uwsgi_rss',
         {u'app': u'rough-snowflake',
          u'instance': u'rough-snowflake-web'},
         351182848.0, timestamps[1])]

    assert metrics[2].name == 'uwsgi_workers'
    assert metrics[2].documentation == 'UWSGI workers'
    assert metrics[2].type == 'gauge'
    assert metrics[2].samples == [
        (u'uwsgi_workers',
         {u'app': u'rough-snowflake',
          u'instance': u'rough-snowflake-web',
          u'status': u'busy'},
         6.0, timestamps[2]),
        (u'uwsgi_workers',
         {u'app': u'rough-snowflake',
          u'instance': u'rough-snowflake-web',
          u'status': u'idle'},
         10.0, timestamps[3])]

    assert metrics[3].name == 'zfs_total_bytes'
    assert metrics[3].samples == [
        (u'zfs_total_bytes',
         {u'instance': u'rough-snowflake-db'},
         23243473482, timestamps[4]),
    ]


def test_implicit_config(zabbixserver, zabbix_exporter_cli):
    args = ['--url', zabbixserver.url,
            '--login', 'demo', '--password', 'demo', '--port', '9224', '--verbose']
    zabbix_exporter_cli(args)
    response = requests.get('http://localhost:9224/metrics/')
    metrics = [m for m in text_string_to_metric_families(response.text)
               if not m.name.startswith('zabbix_exporter') and not m.name.startswith('process_')]

    assert [m.name for m in metrics] == [
        u'local_metric_redis_connected_clients_6380_',
        u'local_metric_uwsgi_sum_rough_snowflake_rss_',
        u'local_metric_uwsgi_workers_rough_snowflake_busy_',
        u'local_metric_uwsgi_workers_rough_snowflake_idle_',
        u'local_metric_uwsgi_workers_rough_snowflake_total_',
        u'wtf',
        u'zfs_total_bytes'
    ]


def test_exporter_returns_500_on_scrape_errors(zabbixserver, zabbix_exporter_cli):
    args = ['--url', zabbixserver.url,
            '--no-verify', '--config', 'tests/configs/explicit_config.yaml',
            '--login', 'demo', '--password', 'demo', '--port', '9224', '--verbose']
    zabbix_exporter_cli(args)
    zabbixserver.serve_content('', 500)
    response = requests.get('http://localhost:9224/metrics/')
    assert response.status_code == 500
