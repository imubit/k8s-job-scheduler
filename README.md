<!-- These are examples of badges you might want to add to your README:
     please update the URLs accordingly

[![Built Status](https://api.cirrus-ci.com/github/<USER>/k8s-job-scheduler.svg?branch=main)](https://cirrus-ci.com/github/<USER>/k8s-job-scheduler)
[![ReadTheDocs](https://readthedocs.org/projects/k8s-job-scheduler/badge/?version=latest)](https://k8s-job-scheduler.readthedocs.io/en/stable/)
[![Coveralls](https://img.shields.io/coveralls/github/<USER>/k8s-job-scheduler/main.svg)](https://coveralls.io/r/<USER>/k8s-job-scheduler)
[![PyPI-Server](https://img.shields.io/pypi/v/k8s-job-scheduler.svg)](https://pypi.org/project/k8s-job-scheduler/)
[![Conda-Forge](https://img.shields.io/conda/vn/conda-forge/k8s-job-scheduler.svg)](https://anaconda.org/conda-forge/k8s-job-scheduler)
[![Monthly Downloads](https://pepy.tech/badge/k8s-job-scheduler/month)](https://pepy.tech/project/k8s-job-scheduler)
[![Twitter](https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter)](https://twitter.com/k8s-job-scheduler)
-->

[![Project generated with PyScaffold](https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold)](https://pyscaffold.org/)
[![Coveralls](https://img.shields.io/coveralls/github/imubit/k8s-job-scheduler/main.svg)](https://coveralls.io/r/imubit/k8s-job-scheduler)
[![PyPI-Server](https://img.shields.io/pypi/v/k8s-job-scheduler.svg)](https://pypi.org/project/k8s-job-scheduler/)


# k8s-job-scheduler

A package for managing Kubernetes jobs and cron jobs from Python. It allows running CLI scripts and Python functions within native Kubernetes job engine.
No need to package separate Docker images with functions to be executed - the package can remotely "inject" the Python function using `dill` into publicly available Docker images.

## Installation

```python
pip install k8s-job-scheduler
```

## Getting Started

```commandline
from k8s_job_scheduler import JobManager

def add(a, b):
    return a + b

manager = JobManager(docker_image="python:3.11.1-slim-bullseye")
job = manager.create_job(add, 1, 2)

```

This example will create a Kubernetes job and run the function `add` with arguments 1 and 2 inside Python Docker container.


## Other Prerequisites

### Executing Python functions withing Kubernetes containers

* Docker images should include Python interpreter and all the dependencies required to execute the function.
* `dill` package is used to send the execution function and it's arguments when Docker container is created. If you wish to use standard Python Docker images or custom images which does not have `dill` package preinstalled, it is possible to specify `dynamic_dill_install=True` when calling `create_instant_python_job`. In this case `dill` will be dynamically installed before running the code.
