import time

import pytest

from k8s_job_scheduler.job_manager import K8S_DEFAULT_NAMESPACE, JobManager

DOCKER_IMAGE_PYTHON = "python:3.11.1-slim-bullseye"


@pytest.fixture
def jobman(request, docker_image=DOCKER_IMAGE_PYTHON, env=None):
    if hasattr(request, "param"):
        docker_image = request.param.get("docker_image", docker_image)
        env = request.param.get("env", env)

    jobman = JobManager(
        docker_image=docker_image, env=env, namespace=K8S_DEFAULT_NAMESPACE
    )
    jobman.init()

    # Clean old pods
    for pod in jobman.list_pods():
        jobman.delete_pod(pod)

    # Clean old jobs
    for job in jobman.list_jobs():
        jobman.delete_job(job)

    # Clean old cron jobs
    for job in jobman.list_scheduled_jobs():
        jobman.delete_scheduled_job(job)

    time.sleep(0.3)

    return jobman
