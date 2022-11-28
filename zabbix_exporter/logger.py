import coloredlogs
import logging

cmd_logger = logging.getLogger(__name__)
coloredlogs.install(fmt='%(asctime)s %(levelname)s %(message)s',
                    level='DEBUG', logger=cmd_logger)
