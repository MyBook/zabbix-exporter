# coding: utf-8


class SortedDict(dict):
    """Hackish container to guarantee consistent label sequence for prometheus"""
    def keys(self):
        return sorted(super(SortedDict, self).keys())

    def values(self):
        return [self[key] for key in self.keys()]
