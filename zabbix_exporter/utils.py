import re
from prometheus_client import Counter, Gauge, CollectorRegistry


def sanitize_key(string):
    return re.sub('[^a-zA-Z0-9:_]+', '_', string)


def prepare_regex(key_pattern):
    return re.escape(key_pattern).replace('\*', '([^,]*?)')


class SortedDict(dict):
    """Dictionary wrapper to guarantee consistent label sequence for prometheus"""

    def keys(self):
        return sorted(super(SortedDict, self).keys())

    def values(self):
        return [self[key] for key in self.keys()]


class LocalCollectorRegistry(CollectorRegistry):
    def __init__(self):
        super().__init__()

        self.scrapes_total = Counter('zabbix_exporter_scrapes_total', 'Number of scrapes', registry=self)
        self.api_requests_total = Counter('zabbix_exporter_api_requests_total', 'Requests to Zabbix API', registry=self)
        self.api_bytes_total = Counter('zabbix_exporter_api_bytes_total',
                                       'Bytes in response from Zabbix API (after decompression)',
                                       registry=self)
        self.api_seconds_total = Counter('zabbix_exporter_api_seconds_total', 'Seconds spent fetching from Zabbix API',
                                         registry=self)
        self.metrics_count_total = Gauge('zabbix_exporter_metrics_total', 'Number of exported zabbix metrics',
                                         registry=self)
        self.series_count_total = Gauge('zabbix_exporter_series_total', 'Number of exported zabbix values',
                                        registry=self)


exporter_registry = LocalCollectorRegistry()
