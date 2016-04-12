# coding: utf-8
import signal
from functools import partial
from time import sleep

import requests
import sys

if sys.version_info[0] < 3:
    import subprocess32 as subprocess  # backported stdlib package
else:
    import subprocess
from zabbix_exporter.prometheus import text_string_to_metric_families
from pytest_localserver.http import WSGIServer
from werkzeug.wrappers import Response, Request


def zabbix_fake_app(environ, start_response):
    request = Request(environ)
    request_body = request.get_data(as_text=True)

    if getattr(zabbix_fake_app, 'status', False):
        response = Response(status=zabbix_fake_app.status)
        response.data = zabbix_fake_app.content
        return response(environ, start_response)

    response = Response(status=200, headers=[('Content-type', 'application/json')])
    if '"method": "user.login"' in request_body:
        json_string = '{"jsonrpc":"2.0","result":"9287f336ffb611e586aa5e5517507c66","id":0}'
    elif '"method": "host.get"' in request_body:
        json_string = open('tests/fixtures/host.get_success.json').read()
    elif '"method": "item.get"' in request_body:
        json_string = open('tests/fixtures/items.get_success.json').read()
    else:
        json_string = 'Unrecognized test request'
    response.data = json_string
    return response(environ, start_response)


def pytest_funcarg__zabbixserver(request):
    server = WSGIServer(application=zabbix_fake_app)
    server.start()
    request.addfinalizer(server.stop)
    def serve_content(self, content, status):
        self.app.content = content
        self.app.status = status
    server.serve_content = partial(serve_content, server)
    return server


def test_explicit_config(zabbixserver):
    args = ['zabbix_exporter', '--url', zabbixserver.url,
            '--no-verify', '--config', 'tests/configs/explicit_config.yaml',
            '--login', 'demo', '--password', 'demo', '--port', '9224', '--verbose']
    p = subprocess.Popen([' '.join(args)], stdout=subprocess.PIPE, shell=True)
    sleep(1)
    response = requests.get('http://localhost:9224/metrics/')
    p.send_signal(signal.SIGINT)  # ensure coverage is collected
    metrics = list(text_string_to_metric_families(response.text))

    assert len(metrics) == 3

    assert metrics[0].name == 'uwsgi_rss'
    assert metrics[0].documentation == 'UWSGI RSS sum'
    assert metrics[0].type == 'gauge'
    assert metrics[0].samples == [
        (u'uwsgi_rss',
         {u'app': u'rough-snowflake',
          u'instance': u'rough-snowflake-web'},
         351182848.0,
         1460359130)]

    assert metrics[1].name == 'uwsgi_workers'
    assert metrics[1].documentation == 'UWSGI workers'
    assert metrics[1].type == 'gauge'
    assert metrics[1].samples == [
        (u'uwsgi_workers',
         {u'app': u'rough-snowflake',
          u'instance': u'rough-snowflake-web',
          u'status': u'busy'},
         6.0, 1460359143),
        (u'uwsgi_workers',
         {u'app': u'rough-snowflake',
          u'instance': u'rough-snowflake-web',
          u'status': u'idle'},
         10.0, 1460359143)]

    assert metrics[2].name == 'zfs_total_bytes'
    assert metrics[2].samples == [
        (u'zfs_total_bytes',
         {u'instance': u'rough-snowflake-db'},
         23243473482, 1460359140),
    ]

def test_implicit_config(zabbixserver):
    args = ['zabbix_exporter', '--url', zabbixserver.url,
            '--login', 'demo', '--password', 'demo', '--port', '9224', '--verbose']
    p = subprocess.Popen([' '.join(args)], stdout=subprocess.PIPE, shell=True)
    sleep(1)
    response = requests.get('http://localhost:9224/metrics/')
    p.send_signal(signal.SIGINT)  # ensure coverage is collected
    metrics = list(text_string_to_metric_families(response.text))

    assert [m.name for m in metrics] == [
        u'local_metric_uwsgi_sum_rough_snowflake_rss_',
        u'local_metric_uwsgi_workers_rough_snowflake_busy_',
        u'local_metric_uwsgi_workers_rough_snowflake_idle_',
        u'local_metric_uwsgi_workers_rough_snowflake_total_',
        u'wtf',
        u'zfs_total_bytes']


def test_exporter_returns_500_on_scrape_errors(zabbixserver):
    args = ['zabbix_exporter', '--url', zabbixserver.url,
            '--no-verify', '--config', 'tests/configs/explicit_config.yaml',
            '--login', 'demo', '--password', 'demo', '--port', '9224', '--verbose']
    p = subprocess.Popen([' '.join(args)], stdout=subprocess.PIPE, shell=True)
    sleep(1)
    zabbixserver.serve_content('', 500)
    response = requests.get('http://localhost:9224/metrics/')
    p.send_signal(signal.SIGINT)  # ensure coverage is collected
    assert response.status_code == 500


