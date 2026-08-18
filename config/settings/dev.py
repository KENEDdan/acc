import sys

from .base import *

DEBUG = True

# Disabled automatically under `manage.py test` — the rate-limit cache is a
# real shared Redis instance (correct for prod, where limits must be shared
# across worker processes), which unlike the DB isn't rolled back between
# tests. Repeated test runs within the same window would eventually start
# tripping the limits and failing unrelated tests.
RATELIMIT_ENABLE = 'test' not in sys.argv
