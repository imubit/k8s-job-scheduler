import base64
import logging
import os
import sys
import zlib

import dill

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

logger = logging.getLogger(__name__)

K8S_ENV_VAR_NAME = "K8S_JOB_FUNC"


def execute():
    try:
        func_def = os.getenv(K8S_ENV_VAR_NAME)
        if not func_def:
            print(
                f"Environment var '{K8S_ENV_VAR_NAME}' is not set, nothing to execute."
            )
            sys.exit(-1)

        current_job = dill.loads(
            zlib.decompress(base64.urlsafe_b64decode(func_def.encode()))
        )
        return current_job.execute()
    except Exception as e:
        logger.fatal(e)
        raise


if __name__ == "__main__":
    execute()
