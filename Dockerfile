FROM python:3.5-slim
MAINTAINER The MyBook Developers <dev@mybook.ru>

RUN groupadd zabbix_exporter && useradd --no-create-home --gid zabbix_exporter zabbix_exporter

COPY config-example.yml /zabbix_exporter/zabbix_exporter.yml

RUN pip install https://github.com/Eksmo/zabbix-exporter/archive/39b007f1968731b13c652e59569c6f1550eabb84.zip#egg=zabbix_exporter

VOLUME [ "/zabbix_exporter" ]

USER zabbix_exporter
WORKDIR /zabbix_exporter
ENTRYPOINT ["/usr/local/bin/zabbix_exporter"]
CMD [ "--config=/zabbix_exporter/zabbix_exporter.yml", \
      "--timeout=10"]
