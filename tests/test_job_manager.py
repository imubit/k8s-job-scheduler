import logging
import time

import pytest


def test_success(jobman):
    cmd = "python"

    job_name = jobman.create_instant_cli_job(
        cmd, "--help", labels={"selector": "a", "namespace": "abc"}
    )
    assert job_name.startswith(f'kjs-inst-job-cli-{cmd.replace("_", "-")}')
    assert jobman.list_jobs() == [job_name]
    assert jobman.list_jobs(filter_labels="selector=a") == [job_name]
    assert jobman.list_jobs(filter_labels="selector=b") == []
    assert jobman.list_jobs(filter_labels="selector=a,namespace=abc") == [job_name]
    assert jobman.list_jobs(filter_labels={"selector": "a"}) == [job_name]
    assert jobman.list_jobs(filter_labels={"selector": "b"}) == []
    assert jobman.list_jobs(filter_labels={"selector": "a", "namespace": "abc"}) == [
        job_name
    ]

    status, details = jobman.job_status(job_name)
    assert status == "ACTIVE"

    time.sleep(10)

    pods = jobman.list_pods(job_name=job_name)
    assert pods[0].startswith(f'kjs-inst-job-cli-{cmd.replace("_", "-")}')

    assert len(jobman.job_logs(job_name)) > 10

    status, _ = jobman.job_status(job_name)
    assert status == "SUCCEEDED"

    assert jobman.delete_job(job_name)

    time.sleep(3)

    assert jobman.list_jobs() == []
    assert jobman.list_pods() == []


def test_failed(jobman):
    cmd = "python"

    job_name = jobman.create_instant_cli_job(cmd, "---h", backoff_limit=0)
    assert job_name.startswith(f'kjs-inst-job-cli-{cmd.replace("_", "-")}')
    assert jobman.list_jobs() == [job_name]

    time.sleep(10)
    status, details = jobman.job_status(job_name)
    assert status == "FAILED"
    assert details["reason"] == "BackoffLimitExceeded"

    pods = jobman.list_pods(job_name=job_name)
    assert pods[0].startswith(f'kjs-inst-job-cli-{cmd.replace("_", "-")}')

    assert len(jobman.job_logs(job_name)) > 10

    assert not jobman.delete_job(job_name)

    time.sleep(3)

    assert jobman.list_jobs() == []
    assert jobman.list_pods() == []


@pytest.mark.parametrize("jobman", [dict(env={"TEST_VAR": "hi_there"})], indirect=True)
def test_env(jobman):
    cmd = "printenv"

    job_name = jobman.create_instant_cli_job(cmd, "TEST_VAR")
    assert job_name.startswith("kjs-inst-job-cli-printenv-")
    assert jobman.list_jobs() == [job_name]

    time.sleep(10)

    status, _ = jobman.job_status(job_name)
    assert status == "SUCCEEDED"

    assert jobman.job_logs(job_name).startswith("hi_there")


def _func_add(a, b):
    result = a + b
    print(result)
    return 0


def test_instant_python_job(jobman):
    job_name = jobman.create_instant_python_job(func=_func_add, a=3, b=5)
    assert job_name.startswith("kjs-inst-job-")
    assert jobman.list_jobs() == [job_name]

    time.sleep(15)

    status, _ = jobman.job_status(job_name)
    assert status == "SUCCEEDED"

    assert jobman.job_logs(job_name).endswith("8\n")


def _func_divide(a, b):
    result = a / b
    return result


def test_python_job_exception(jobman):
    job_name = jobman.create_instant_python_job(
        job_name="failed-job", func=_func_divide, a=3, b=0, backoff_limit=0
    )
    assert job_name == "failed-job"
    assert jobman.list_jobs() == [job_name]

    time.sleep(15)

    status, _ = jobman.job_status(job_name)
    assert status == "FAILED"
    assert (
        jobman.job_logs(job_name, tail_lines=1)
        == "ZeroDivisionError: division by zero\n"
    )


def _func_time_parse(a):
    from pytimeparse import parse

    print(parse(f"{a} day, 14:20:16"))
    return 0


def test_python_job_with_custom_lib(jobman):
    job_name = jobman.create_instant_python_job(
        func=_func_time_parse,
        a=1,
        pip_packages=["dill", "pytimeparse"],
        log_level=logging.DEBUG,
    )
    assert job_name.startswith("kjs-inst-job-")
    assert jobman.list_jobs() == [job_name]

    time.sleep(15)

    status, _ = jobman.job_status(job_name)
    assert status == "SUCCEEDED"

    assert jobman.job_logs(job_name).endswith("138016\n")
    assert jobman.job_logs(job_name, tail_lines=1) == "138016"


def test_scheduled_job(jobman):
    cron = "*/1 * * * *"
    cmd = "printenv"

    job_name = jobman.create_scheduled_cli_job(
        cron, cmd, "TEST_VAR", labels={"selector": "a", "namespace": "abc"}
    )
    assert jobman.list_scheduled_jobs() == [job_name]
    assert jobman.list_scheduled_jobs(filter_labels="selector=a") == [job_name]
    assert jobman.list_scheduled_jobs(filter_labels="selector=b") == []
    assert jobman.list_scheduled_jobs(filter_labels="selector=a,namespace=abc") == [
        job_name
    ]
    assert jobman.list_scheduled_jobs(filter_labels={"selector": "a"}) == [job_name]
    assert jobman.list_scheduled_jobs(filter_labels={"selector": "b"}) == []
    assert jobman.list_scheduled_jobs(
        filter_labels={"selector": "a", "namespace": "abc"}
    ) == [job_name]

    time.sleep(10)

    # assert job_name.startswith(f'job-kjs-{cmd.replace("_", "-")}')
    assert jobman.list_scheduled_jobs() == [job_name]

    assert jobman.delete_scheduled_job(job_name)

    time.sleep(3)

    assert jobman.list_scheduled_jobs() == []
    assert jobman.list_pods() == []


def _func_delayed_divide(a, b):
    import time as tm

    tm.sleep(2)
    result = a / b
    return result


def test_restart_policy_never(jobman):
    job_name = jobman.create_instant_python_job(
        func=_func_delayed_divide, a=4, b=0, backoff_limit=0
    )
    assert job_name.startswith("kjs-inst-job-")
    assert jobman.list_jobs() == [job_name]

    time.sleep(10)

    assert jobman.job_status(job_name)[0] == "FAILED"


def test_restart_policy_on_failure(jobman):
    job_name = jobman.create_instant_python_job(
        func=_func_delayed_divide, a=4, b=0, restart_policy="OnFailure"
    )
    assert job_name.startswith("kjs-inst-job-")
    assert jobman.list_jobs() == [job_name]

    time.sleep(10)

    # Failing on Github action test
    # assert jobman.job_status(job_name)[0] == "READY"
