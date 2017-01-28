FROM python:3.5-slim
MAINTAINER The MyBook Developers <dev@mybook.ru>

RUN groupadd zabbix_exporter && useradd --no-create-home --gid zabbix_exporter zabbix_exporter
COPY . /tmp/zabbix_exporter
WORKDIR /tmp/zabbix_exporter
RUN pip install -e .

COPY config-example.yml /zabbix_exporter/zabbix_exporter.yml

EXPOSE 9224
VOLUME [ "/zabbix_exporter" ]

USER zabbix_exporter
WORKDIR /zabbix_exporter
ENTRYPOINT [ "/usr/local/bin/zabbix_exporter" ]
CMD [ "--config=/zabbix_exporter/zabbix_exporter.yml", \
      "--timeout=10" ]
