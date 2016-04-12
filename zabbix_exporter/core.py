# coding: utf-8
import logging
import re

import pyzabbix
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY

from .compat import BaseHTTPRequestHandler
from .prometheus import GaugeMetricFamily, generate_latest
from .utils import SortedDict

logger = logging.getLogger(__name__)



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
                metric = attrs.get('name', metric)
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
        logger.debug('Polling...')
        items = self.zapi.item.get(output=['name', 'key_', 'hostid', 'lastvalue', 'lastclock', 'value_type'],
                                   sortfield='key_')
        exposed_metrics = set()
        gauge = None

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
                             int(item['lastclock']))
        if gauge:
            yield gauge

    def is_exportable(self, item):
        return item['value_type'] in {'0', '3'}  # only numeric/float values


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            response = generate_latest(REGISTRY)
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
