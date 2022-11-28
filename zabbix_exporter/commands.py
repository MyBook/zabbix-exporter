import click
from prometheus_client import REGISTRY
from qrconfig import QRYamlConfig

from .server import create_exporter_server
from .zabbix_collector import ZabbixSelectiveCollector
from .logger import cmd_logger


def validate_settings(settings):
    if not settings['url']:
        raise Exception('Please provide Zabbix API URL')
    if not settings['login']:
        raise Exception('Please provide Zabbix username')
    if not settings['password']:
        raise Exception('Please provide Zabbix account password')


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
def cli(**settings):
    """Zabbix metrics exporter for Prometheus

       Use config file to map zabbix metrics names/labels into prometheus.
       Config below transforms this:

           local.metric[uwsgi,workers,myapp,busy] = 8
           local.metric[uwsgi,workers,myapp,idle] = 6

       into familiar Prometheus gauges:

           uwsgi_workers{instance="host1",app="myapp",status="busy"} 8
           uwsgi_workers{instance="host1",app="myapp",status="idle"} 6

       YAML config example:

       \b
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
    """

    validate_settings(settings)

    if settings['verbose']:
        cmd_logger.setLevel('DEBUG')
    else:
        cmd_logger.setLevel('ERROR')

    exporter_config = QRYamlConfig(settings['config']) if settings['config'] else dict()

    # create zabbix collector
    collector = ZabbixSelectiveCollector(
        explicit_metrics=exporter_config.parsing.explicit_metrics,
        enable_timestamps=exporter_config.parsing.enable_timestamps,
        enable_empty_hosts=exporter_config.parsing.enable_empty_hosts,
        metrics=exporter_config.metrics,
        zabbix_config=dict(base_url=settings['url'].rstrip('/'),
                           login=settings['login'],
                           password=settings['password'],
                           verify_tls=settings['verify_tls'],
                           timeout=settings['timeout'], ),
    )
    REGISTRY.register(collector)

    # setup server
    server = create_exporter_server(int(settings['port']))
    click.echo('Exporter for {base_url}, user: {login}, password: ***'.format(
        base_url=settings['url'].rstrip('/'),
        login=settings['login'],
        password=settings['password']
    ))

    click.echo('Exporting Zabbix metrics on http://0.0.0.0:{}'.format(settings['port']))
    server.serve_forever()
