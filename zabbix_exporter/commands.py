# coding: utf-8
import logging

import click
import sys
import yaml
from prometheus_client import REGISTRY

import zabbix_exporter
from zabbix_exporter.core import ZabbixCollector, MetricsHandler
from .compat import HTTPServer

logger = logging.getLogger(__name__)


def validate_settings(settings):
    if not settings['url']:
        click.echo('Please provide Zabbix API URL', err=True)
        sys.exit(1)
    if not settings['login']:
        click.echo('Please provide Zabbix username', err=True)
        sys.exit(1)
    if not settings['password']:
        click.echo('Please provide Zabbix account password', err=True)
        sys.exit(1)
    return True


@click.command()
@click.option('--config', help='Path to exporter config',
              type=click.Path(exists=True))
@click.option('--port', default=9224, help='Port to serve prometheus stats [default: 9224]')
@click.option('--url', help='HTTP URL for zabbix instance')
@click.option('--login', help='Zabbix username')
@click.option('--password', help='Zabbix password')
@click.option('--verify-tls/--no-verify', help='Enable TLS cert verification [default: true]', default=True)
@click.option('--timeout', help='API read/connect timeout', default=5)
@click.option('--verbose', is_flag=True)
@click.option('--dump-metrics', help='Output all metrics for human to write yaml config', is_flag=True)
@click.option('--version', is_flag=True)
@click.option('--return-server', is_flag=True, help='Developer flag. Please ignore.')
def cli(**settings):
    """Zabbix metrics exporter for Prometheus

       Use config file to map zabbix metrics names/labels into prometheus.
       Config below transfroms this:

           local.metric[uwsgi,workers,myapp,busy] = 8
           local.metric[uwsgi,workers,myapp,idle] = 6

       into familiar Prometheus gauges:

           uwsgi_workers{instance="host1",app="myapp",status="busy"} 8
           uwsgi_workers{instance="host1",app="myapp",status="idle"} 6

       YAML:

       \b
           metrics:
             - key: 'local.metric[uwsgi,workers,*,*]'
               name: 'uwsgi_workers'
               labels:
                 app: $1
                 status: $2
               reject:
                 - 'total'
    """
    if settings['version']:
        click.echo('Version %s' % zabbix_exporter.__version__)
        return

    if not validate_settings(settings):
        return

    if settings['config']:
        exporter_config = yaml.safe_load(open(settings['config']))
    else:
        exporter_config = {}

    base_logger = logging.getLogger('zabbix_exporter')
    handler = logging.StreamHandler()
    base_logger.addHandler(handler)
    base_logger.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', "%Y-%m-%d %H:%M:%S"))
    if settings['verbose']:
        base_logger.setLevel(logging.DEBUG)

    collector = ZabbixCollector(
        base_url=settings['url'].rstrip('/'),
        login=settings['login'],
        password=settings['password'],
        verify_tls=settings['verify_tls'],
        timeout=settings['timeout'],
        **exporter_config
    )

    if settings['dump_metrics']:
        return dump_metrics(collector)

    REGISTRY.register(collector)
    httpd = HTTPServer(('', int(settings['port'])), MetricsHandler)
    click.echo('Exporter for {base_url}, user: {login}, password: ***'.format(
        base_url=settings['url'].rstrip('/'),
        login=settings['login'],
        password=settings['password']
    ))
    if settings['return_server']:
        return httpd
    click.echo('Exporting Zabbix metrics on http://0.0.0.0:{}'.format(settings['port']))
    httpd.serve_forever()


def dump_metrics(collector):
    for item in collector.zapi.item.get(output=['name', 'key_', 'hostid', 'lastvalue', 'lastclock', 'value_type'],
                                        sortfield='key_'):
        click.echo('{host:20}{key} = {value}\n{name:>20}'.format(
            host=collector.host_mapping.get(item['hostid'], item['hostid']),
            key=item['key_'],
            value=item['lastvalue'],
            name=item['name']
        ))
    return
