"""
    Dummy conftest.py for k8s_job_scheduler.

    If you don't know what this is for, just leave it empty.
    Read more about conftest.py under:
    - https://docs.pytest.org/en/stable/fixture.html
    - https://docs.pytest.org/en/stable/writing_plugins.html
"""

import time

import psycopg2
import pytest

from k8s_job_scheduler.job_manager import JobManager

K8S_NAMESPACE = "k8s-job-scheduler"
DOCKER_IMAGE_PYTHON = "python:3.11.7-slim-bullseye"
DOCKER_IMAGE_POSTGRES = "postgres:15"
POSTGRES_USER = "postgres"
POSTGRES_PASS = "q1234567"
POSTGRES_HOST = "postgres_db"
POSTGRES_URI = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:5432/postgres"
)


@pytest.fixture
def jobman(request, docker_image=DOCKER_IMAGE_PYTHON, env=None):
    if hasattr(request, "param"):
        docker_image = request.param.get("docker_image", docker_image)
        env = request.param.get("env", env)

    jobman = JobManager(namespace=K8S_NAMESPACE, docker_image=docker_image, env=env)
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


@pytest.fixture
def psql():
    conn = psycopg2.connect(dsn=POSTGRES_URI)
    conn.autocommit = True

    # Drop all tables
    with conn.cursor() as curs:
        curs.execute(
            """DO $$ DECLARE
                r RECORD;
            BEGIN
                -- if the schema you operate on is not "current", you will want to
                -- replace current_schema() in query with 'schematodeletetablesfrom'
                -- *and* update the generate 'DROP...' accordingly.
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;"""
        )

    return conn
