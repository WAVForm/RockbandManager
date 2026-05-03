import logging, logging.config
import uvicorn
from rockbandmanager.utils.db import init_db

#from rv_scraper import RVScraper
#from database_manager import DatabaseManager
from rockbandmanager.routes.server import router

if __name__ == "__main__":
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': 'server.log',
                'formatter': 'default',
            },
            'stdout': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
        },
        'loggers': {
            'CentralServer': {
                'handlers': ['file', 'stdout'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'RVScraper': {
                'handlers': ['file', 'stdout'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'XLSXManager': {
                'handlers': ['file', 'stdout'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'DatabaseManager': {
                'handlers': ['file', 'stdout'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    })     
    init_db()

    uvicorn.run(router, host="0.0.0.0", port=8000)
