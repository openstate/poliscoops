import os

# Register custom serializer for Celery that allows for encoding and decoding
# Python datetime objects (and potentially other ones)
from kombu.serialization import register
from ocd_backend.serializers import encoder, decoder

register('ocd_serializer', encoder, decoder, content_encoding='binary',
         content_type='application/ocd-msgpack')

CELERY_CONFIG = {
    'BROKER_URL': 'redis://redis:6379/0',
    'CELERY_ACCEPT_CONTENT': ['ocd_serializer'],
    'CELERY_TASK_SERIALIZER': 'ocd_serializer',
    'CELERY_RESULT_SERIALIZER': 'ocd_serializer',
    'CELERY_RESULT_BACKEND': 'ocd_backend.result_backends:OCDRedisBackend+redis://redis:6379/0',
    'CELERY_IGNORE_RESULT': True,
    'CELERY_DISABLE_RATE_LIMITS': True,
    # Expire results after 30 minutes; otherwise Redis will keep
    # claiming memory for a day
    'CELERY_TASK_RESULT_EXPIRES': 1800
}

LOGGING = {
    'version': 1,
    'formatters': {
        'console': {
            'format': '[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'formatter': 'console',
            'filename': 'log/backend.log'
        }
    },
    'loggers': {
        'ocd_backend': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        }
    }
}

ELASTICSEARCH_HOST = 'elasticsearch'
ELASTICSEARCH_PORT = 9200

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

# The path of the directory used to store temporary files
TEMP_DIR_PATH = os.path.join(ROOT_PATH, 'temp')

# The path of the JSON file containing the sources config
SOURCES_CONFIG_FILE = os.path.join(ROOT_PATH, 'sources/*.json')

# The name of the index containing documents from all sources
COMBINED_INDEX = 'pfl_combined_index'

# The default prefix used for all data
DEFAULT_INDEX_PREFIX = 'pfl'

RESOLVER_BASE_URL = 'https://api.poliflw.nl/v0/resolve'
RESOLVER_URL_INDEX = 'pfl_resolver'

# The User-Agent that is used when retrieving data from external sources
USER_AGENT = 'Poliscoops API/0.1 (+https://poliscoops.eu/)'

# URL where of the API instance that should be used for management commands
# Should include API version and a trailing slash.
# Can be overridden in the CLI when required, for instance when the user wants
# to download dumps from another API instance than the one hosted by OpenState
API_URL = 'http://frontend:5000/v0/'

# define the location of pdftotext
PDF_TO_TEXT = u'pdftotext'
PDF_MAX_MEDIABOX_PIXELS = 5000000

# The path of the directory used to store linkmaps
LINKMAP_PATH = os.path.join(ROOT_PATH, 'data/linkmaps')

# Activitystram 2.0 objects types
AS2_NAMESPACE = u'https://www.poliflw.nl/ns/voc/'
AS2_OBJECTS = [
    "actor",
    "attachment",
    "attributedTo",
    "audience",
    "bcc",
    "bto",
    "cc",
    "context",
    "current",
    "first",
    "generator",
    "icon",
    "image",
    "inReplyTo",
    "instrument",
    "last",
    "location",
    "items",
    "oneOf",
    "anyOf",
    "origin",
    "next",
    "object",
    "prev",
    "preview",
    "result",
    "replies",
    "tag",
    "target",
    "to",
    "url",
    "partOf",
    "subject",
    "relationship",
    "describes"
]
AS2_TRANSLATION_TYPES = [
    "Note"
]
AS2_TRANSLATION_LANGUAGES = [
    'en', 'de', 'fr'
]

AZURE_TEXT_MAX_LENGTH = 5000

# Allow any settings to be defined in local_settings.py which should be
# ignored in your version control system allowing for settings to be
# defined per machine.
try:
    from local_settings import *
except ImportError:
    pass
