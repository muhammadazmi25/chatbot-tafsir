import logging
import logging.config
import sys

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - [TAFSIR] - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s - [TAFSIR] - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    },
    'loggers': {
        'app': {'level': 'DEBUG', 'handlers': ['console'], 'propagate': False},
        'uvicorn': {'level': 'INFO', 'handlers': ['console'], 'propagate': False},
        'uvicorn.error': {'level': 'INFO', 'handlers': ['console'], 'propagate': False},
        'uvicorn.access': {'level': 'WARNING', 'handlers': ['console'], 'propagate': False},
    }
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f'app.{name}')
