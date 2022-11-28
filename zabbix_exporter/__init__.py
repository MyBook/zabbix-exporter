envvar_prefix = 'ZABBIX'
__version__ = '1.0.3'

def main():
    from .commands import cli
    return cli(auto_envvar_prefix=envvar_prefix)