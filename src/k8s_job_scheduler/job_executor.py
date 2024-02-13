import base64
import logging
import os
import sys
import zlib

import dill

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

logger = logging.getLogger(__name__)

JOB_PYTHON_FUNC_ENV_VAR = "JOB_PYTHON_FUNC"


def execute():
    try:
        func_def = os.getenv(JOB_PYTHON_FUNC_ENV_VAR)
        if not func_def:
            print(
                f"Environment var '{JOB_PYTHON_FUNC_ENV_VAR}' is not set, nothing to execute."
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
