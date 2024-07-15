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
            logger.error(
                f"Environment var '{JOB_PYTHON_FUNC_ENV_VAR}' is not set, nothing to execute."
            )
            sys.exit(-1)

        current_job = dill.loads(
            zlib.decompress(base64.urlsafe_b64decode(func_def.encode()))
        )

        logger.info(
            f"=== Starting job {current_job['name']}, submitted from {current_job['host']} "
            f"at {current_job['dt_scheduled'].isoformat()} ==="
        )
        logger.debug(f"Job func: {current_job['func'].__name__}")
        logger.debug(f" Args: {current_job['args']}")
        logger.debug(f" Kwargs: {current_job['kwargs']}")

        return current_job["func"](*current_job["args"], **current_job["kwargs"])

    except Exception as e:
        logger.fatal(e)
        raise


if __name__ == "__main__":
    sys.exit(execute())
