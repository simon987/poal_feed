import logging
import sys
import traceback
from logging import StreamHandler

import requests
from hexlib.misc import rate_limit

logger = logging.getLogger("default")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
for h in logger.handlers:
    logger.removeHandler(h)
logger.addHandler(StreamHandler(sys.stdout))

UA = "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:83.0) Gecko/20100101 Firefox/83.0"


class Web:
    def __init__(self, rps):
        self.session = requests.Session()
        self._rps = rps

        @rate_limit(self._rps)
        def _get(url, **kwargs):
            if "headers" in kwargs:
                kwargs["headers"]["User-Agent"] = UA
            else:
                kwargs["headers"] = {"User-Agent": UA}
            retries = 3

            while retries > 0:
                retries -= 1
                try:
                    return self.session.get(url, **kwargs)
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    logger.warning("Error with request %s: %s" % (url, str(e)))
            raise Exception("Gave up request after maximum number of retries")

        self._get = _get

    def get(self, url, **kwargs):
        try:
            r = self._get(url, **kwargs)

            logger.debug("GET %s <%d>" % (url, r.status_code))
            return r
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            logger.error(str(e) + traceback.format_exc())
            return None
