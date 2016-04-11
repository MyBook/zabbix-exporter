# coding: utf-8
from zabbix_exporter.core import SortedDict


def test_sorted_keys_dict():
    d = SortedDict()
    for i, letter in enumerate('clkefgnhidjmbaop'):
        d[letter] = i
    assert ''.join(d.keys()) == 'abcdefghijklmnop'
    assert '-'.join(map(str, d.values())) == '13-12-0-9-3-4-5-7-8-10-2-1-11-6-14-15'
