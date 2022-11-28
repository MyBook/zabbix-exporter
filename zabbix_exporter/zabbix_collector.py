import copy
from collections import OrderedDict
from functools import reduce
from typing import List

import pyzabbix
from prometheus_client.registry import Collector

from .logger import cmd_logger
from .prometheus import MetricFamily
from .utils import *


class ZabbixSelectiveCollector(Collector):
    """
    Zabbix metric collector.
    Sends filtered API requests to Zabbix to obtain only needed instances:
    - hosts (by hosts.get) filtered by name
    - items (by items.get) filtered by key mask and used hosts (both provided by configuration)
    """

    def __init__(self,
                 zabbix_config: dict,
                 metrics: List = None,
                 explicit_metrics: bool = True,
                 enable_timestamps: bool = False,
                 enable_empty_hosts: bool = True):
        """
        :param zabbix_config - a dictionary to setup Zabbix client:
        - required keys: base_url: str, login: str, password: str
        - optional keys: verify_tls:bool, timeout: int

        :param metrics - list of dictionaries with keys, each defines: key, name, lables, reject, hosts, item_names
        """
        self.explicit_metrics = explicit_metrics
        self.enable_timestamps = enable_timestamps
        self.enable_empty_hosts = enable_empty_hosts
        self.metrics = self.__validate_metrics(metrics)

        self.key_patterns = {prepare_regex(metric['key']): metric
                             for metric in self.metrics}

        self.zapi = self.__create_zabbix_client(**zabbix_config)

        self.host_mapping = self.__get_used_hosts()  # hostname: hostid
        self.reverse_host_mapping = {v: k for k, v in self.host_mapping.items()}  # hostid: hostname

    def collect(self):
        series_count = 0

        items = self.__load_zabbix_metrics()

        metric_families = OrderedDict()
        for item in items:
            metric = self.__process_metric(item)
            if not metric:
                continue

            if metric['name'] not in metric_families:
                family = MetricFamily(typ=metric['type'],
                                      name=metric['name'],
                                      documentation=metric['documentation'],
                                      labels=metric['labels_mapping'].keys())
                metric_families[metric['name']] = family
            metric_families[metric['name']].add_metric(
                metric['labels_mapping'].values(), float(item['lastvalue']),
                int(item['lastclock']) if self.enable_timestamps else None)
            series_count += 1

        for f in metric_families.values():
            yield f

        exporter_registry.metrics_count_total.set(len(metric_families))
        exporter_registry.series_count_total.set(series_count)

    def __validate_metrics(self, metrics):
        """use on collector initialization: validate, copy & update metrics configuration"""
        metrics = copy.deepcopy(metrics) if metrics is not None else []

        check_keys = ['key', 'name']

        has_empty_hosts = False
        for m in metrics:
            m_ok = reduce(lambda ok, key: ok & (m.get(key) is not None), check_keys, True)
            if not m_ok:
                raise Exception(
                    f'invalid metric found! required fields: {check_keys}, found: {m} (enable_empty_hosts = {self.enable_empty_hosts})')
            if m.get('hosts') in [None, []]:
                has_empty_hosts = True
                m['hosts'] = []
            if m.get('reject') in [None, []]:
                m['reject'] = []
            if m.get('lables') in [None, []]:
                m['lables'] = dict()

            if m.get('item_names') in [None, []]:
                m['item_names'] = None
            else:
                m['item_names'] = list(map(prepare_regex, m['item_names']))

        if has_empty_hosts:
            if not self.enable_empty_hosts:
                cmd_logger.error(
                    'found empty "hosts" field for one of metrics, but forbidden with "enable_empty_hosts"=False. You may change this behaviour in config ')
                raise Exception('empty "hosts" field')
            else:
                cmd_logger.warning('found empty "hosts" field for one of metrics')

        return metrics

    def __load_zabbix_metrics(self):
        total_items = []
        for metric in self.metrics:
            valid_hosts = [self.host_mapping.get(hname, None) for hname in metric['hosts']]
            if None in valid_hosts:
                cmd_logger.error(f'some of metric hosts not found in host_mapping: metric hosts = {metric["hosts"]}')
                valid_hosts = [h for h in valid_hosts if h is not None]

            key = metric['key']

            params = dict(
                output=['name', 'key_', 'hostid', 'lastvalue', 'lastclock', 'value_type'],
                searchWildcardsEnabled='true',
                search={'key_': key},
                sortfield='key_',
            )
            if len(valid_hosts) != 0:
                params['hostids'] = valid_hosts

            items = self.zapi.item.get(**params)
            total_items.extend(items)

        return total_items

    def __get_used_hosts(self):
        """load info to map host names into host ids"""
        host_names = reduce(lambda acc, metric: acc + metric['hosts'], self.metrics, [])
        host_names = list(set(host_names))

        host_dict = self.zapi.host.get(output=['hostid', 'name'],
                                       filter={'host': host_names})
        if len(host_dict) != len(host_names):
            cmd_logger.error(f'FAILED TO GET ALL HOSTS. required {len(host_names)} hosts, loaded {len(host_dict)}')

        host_dict = {x['name']: x['hostid'] for x in host_dict}
        return host_dict

    def __create_zabbix_client(self, base_url, login, password, verify_tls=True, timeout=None):
        zapi = pyzabbix.ZabbixAPI(base_url, timeout=timeout)
        if not verify_tls:
            import requests.packages.urllib3 as urllib3
            urllib3.disable_warnings()
            zapi.session.verify = verify_tls

        def measure_api_request(r, *args, **kwargs):
            exporter_registry.api_requests_total.inc()
            exporter_registry.api_bytes_total.inc(len(r.content))
            exporter_registry.api_seconds_total.inc(r.elapsed.total_seconds())

        zapi.session.hooks = {'response': measure_api_request}

        zapi.login(login, password)
        return zapi

    def __process_metric(self, item):
        if not self.__is_exportable(item):
            cmd_logger.debug('Dropping unsupported metric %s', item['key_'])
            return

        metric = item['key_']
        metric_options = {}
        labels_mapping = SortedDict()
        for pattern, attrs in self.key_patterns.items():
            match = re.match(pattern, item['key_'])
            if match:
                if attrs['item_names'] is not None:
                    # check item name to fit any of the given patterns
                    name_matches = [re.match(p, item['name']) for p in attrs['item_names']]
                    ok = sum([nm is not None for nm in name_matches]) > 0
                    if not ok:
                        continue
                    else:
                        print('***')

                # process metric name
                metric = attrs.get('name', metric)

                def repl(m):
                    asterisk_index = int(m.group(1))
                    return match.group(asterisk_index)

                metric = re.sub('\$(\d+)', repl, metric)

                # ignore metrics with rejected placeholders
                rejected_matches = [r for r in attrs['reject'] if re.search(r, item['key_'])]
                if rejected_matches:
                    cmd_logger.debug('Rejecting metric %s (matched %s)', rejected_matches[0], metric)
                    continue  # allow to process metric by another rule

                # create labels
                for label_name, match_group in attrs['lables'].items():
                    if match_group[0] == '$':
                        label_value = match.group(int(match_group[1]))
                    else:
                        label_value = match_group
                    labels_mapping[label_name] = label_value
                metric_options = attrs
                break
        else:
            # no key match found
            if self.explicit_metrics:
                cmd_logger.debug('Dropping implicit metric name %s', item['key_'])
                return

        # automatic host -> instance labeling
        # todo: may load all hosts from zabbix hosts.get
        labels_mapping['instance'] = self.reverse_host_mapping.get(item['hostid'], 'unknown_host')

        cmd_logger.debug('Converted: %s -> %s [%s]', item['key_'], metric, labels_mapping)
        return {
            'name': sanitize_key(metric),
            'type': metric_options.get('type', 'untyped'),  # untyped by default
            'documentation': metric_options.get('help', item['name']),
            'labels_mapping': labels_mapping,
        }

    def __is_exportable(self, item):
        return item['value_type'] in {'0', '3'}  # only numeric/float values
