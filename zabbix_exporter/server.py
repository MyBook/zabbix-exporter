from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY
from http.server import HTTPServer, BaseHTTPRequestHandler

from .logger import cmd_logger
from .prometheus import generate_latest
from .utils import exporter_registry


def create_exporter_server(port: int):
    return HTTPServer(('', port), MetricsHandler)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            exporter_registry.scrapes_total.inc()
            response = generate_latest(REGISTRY) + generate_latest(exporter_registry)
            status = 200
        except Exception:
            cmd_logger.exception('Fetch failed')
            response = ''
            status = 500
        self.send_response(status)
        self.send_header('Content-Type', CONTENT_TYPE_LATEST)
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        return
