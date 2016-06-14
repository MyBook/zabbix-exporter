# coding: utf-8
import yaml

from zabbix_exporter.core import SortedDict, ZabbixCollector


def test_sorted_keys_dict():
    d = SortedDict()
    for i, letter in enumerate('clkefgnhidjmbaop'):
        d[letter] = i
    assert ''.join(d.keys()) == 'abcdefghijklmnop'
    assert '-'.join(map(str, d.values())) == '13-12-0-9-3-4-5-7-8-10-2-1-11-6-14-15'


def test_metric_families_dont_override_each_other(zabbixserver):
    config = yaml.safe_load(open('tests/configs/asterisk.conf.yml'))
    collector = ZabbixCollector(base_url=zabbixserver.url, login='demo', password='demo', **config)

    result_json = open('tests/fixtures/items.asterisk_mapping.json').read()
    zabbixserver.serve_content(result_json)
    metrics = [m.samples for m in collector.collect()]

    assert metrics == [
        [(u'uwsgi_exceptions',
          {'app': u'projectA', 'instance': u'rough-snowflake-web'},
          10.0,
          None),
         (u'uwsgi_exceptions',
          {'app': u'projectB', 'instance': u'rough-snowflake-web'},
          1000.0,
          None)
         ],
        [(u'uwsgi_requests',
          {'app': u'projectA', 'instance': u'rough-snowflake-web'},
          100.0,
          None),
         ]
    ]


def test_reject_labels(zabbixserver):
    config = yaml.safe_load(open('tests/configs/reject_labels.conf.yml'))
    collector = ZabbixCollector(base_url=zabbixserver.url, login='demo', password='demo', **config)

    result_json = open('tests/fixtures/items.reject_labels.json').read()
    zabbixserver.serve_content(result_json)
    metrics = [m.samples for m in collector.collect()]

    assert metrics == [
        [(u'zpool_size',
          {'mode': u'used', 'pool': u'tank', 'instance': u'rough-snowflake-db'},
          749471793152,
          None),
         (u'zpool_size',
          {'mode': u'total', 'pool': u'tank', 'instance': u'rough-snowflake-db'},
          970662608896,
          None)
         ],
    ]
