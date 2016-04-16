# coding: utf-8
import logging
import re

import pyzabbix
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Gauge, Summary, CollectorRegistry

from .compat import BaseHTTPRequestHandler
from .prometheus import GaugeMetricFamily, generate_latest
from .utils import SortedDict

logger = logging.getLogger(__name__)


exporter_registry = CollectorRegistry()  # makes sure to collect metrics after ZabbixCollector

scrapes_total = Counter('zabbix_exporter_scrapes_total', 'Number of scrapes', registry=exporter_registry)
api_requests_total = Counter('zabbix_exporter_api_requests_total', 'Requests to Zabbix API', registry=exporter_registry)
api_bytes_total = Counter('zabbix_exporter_api_bytes_total', 'Bytes in response from Zabbix API (after decompression)', registry=exporter_registry)
api_seconds_total = Counter('zabbix_exporter_api_seconds_total', 'Seconds spent fetching from Zabbix API', registry=exporter_registry)
metrics_count_total = Gauge('zabbix_exporter_metrics_total', 'Number of exported zabbix metrics', registry=exporter_registry)
series_count_total = Gauge('zabbix_exporter_series_total', 'Number of exported zabbix values', registry=exporter_registry)


def sanitize_key(string):
    return re.sub('[^a-zA-Z0-9:_]+', '_', string)


def prepare_regex(key_pattern):
    return re.escape(key_pattern).replace('\*', '([^,]*?)')


class ZabbixCollector(object):

    def __init__(self, base_url, login, password, verify_tls, timeout, **options):
        self.options = options
        self.key_patterns = {prepare_regex(metric['key']): metric
                             for metric in options.get('metrics', [])}

        self.zapi = pyzabbix.ZabbixAPI(base_url, timeout=timeout)
        if not verify_tls:
            import requests.packages.urllib3 as urllib3
            urllib3.disable_warnings()
            self.zapi.session.verify = verify_tls

        def measure_api_request(r, *args, **kwargs):
            api_requests_total.inc()
            api_bytes_total.inc(len(r.content))
            api_seconds_total.inc(r.elapsed.total_seconds())
        self.zapi.session.hooks = {'response': measure_api_request}

        self.zapi.login(login, password)

        self.host_mapping = {row['hostid']: row['name']
                             for row in self.zapi.host.get(output=['hostid', 'name'])}

    def process_metric(self, item):
        metric = item['key_']
        metric_options = {}
        labels_mapping = SortedDict()
        for pattern, attrs in self.key_patterns.items():
            match = re.match(pattern, item['key_'])
            if match:
                # process metric name
                metric = attrs.get('name', metric)

                def repl(m):
                    asterisk_index = int(m.group(1))
                    return match.group(asterisk_index)
                metric = re.sub('\$(\d+)', repl, metric)

                # create labels
                for label_name, match_group in attrs.get('labels', {}).items():
                    label_value = match.group(int(match_group[1]))
                    if label_value in attrs.get('labels_reject', {}):
                        logger.debug('Rejecting metric label %s for %s', label_value, metric)
                        return None
                    labels_mapping[label_name] = label_value
                metric_options = attrs
                break
        else:
            if self.options.get('explicit_metrics', False):
                logger.debug('Dropping implicit metric name %s', item['key_'])
                return None

        # automatic host -> instance labeling
        labels_mapping['instance'] = self.host_mapping[item['hostid']]

        return {
            'name': sanitize_key(metric),
            'documentation': metric_options.get('help', item['name']),
            'labels_mapping': labels_mapping,
        }

    def collect(self):
        items = self.zapi.item.get(output=['name', 'key_', 'hostid', 'lastvalue', 'lastclock', 'value_type'],
                                   sortfield='key_')
        api_bytes_total.inc()
        exposed_metrics = set()
        series_count = 0
        gauge = None
        enable_timestamps = self.options.get('enable_timestamps', False)

        for item in items:
            if not self.is_exportable(item):
                logger.debug('Dropping unsupported metric %s', item['key_'])
                continue
            metric = self.process_metric(item)
            if not metric:
                continue

            if metric['name'] not in exposed_metrics:
                if gauge:
                    yield gauge
                gauge = GaugeMetricFamily(name=metric['name'],
                                          documentation=metric['documentation'],
                                          labels=metric['labels_mapping'].keys())
                exposed_metrics.add(metric['name'])
            gauge.add_metric(metric['labels_mapping'].values(), float(item['lastvalue']),
                             int(item['lastclock']) if enable_timestamps else None)
            series_count += 1
        if gauge:
            yield gauge
        metrics_count_total.set(len(exposed_metrics))
        series_count_total.set(series_count)

    def is_exportable(self, item):
        return item['value_type'] in {'0', '3'}  # only numeric/float values


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            scrapes_total.inc()
            response = generate_latest(REGISTRY) + generate_latest(exporter_registry)
            status = 200
        except Exception:
            logger.exception('Fetch failed')
            response = ''
            status = 500
        self.send_response(status)
        self.send_header('Content-Type', CONTENT_TYPE_LATEST)
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        return
