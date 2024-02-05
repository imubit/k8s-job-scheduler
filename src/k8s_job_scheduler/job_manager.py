import json
import logging

from kubernetes import client, config
from kubernetes.client.rest import ApiException

__author__ = "Meir Tseitlin"
__copyright__ = "Imubit"
__license__ = "LGPL-3.0-only"

log = logging.getLogger(__name__)

config.load_kube_config()

K8S_DEFAULT_NAMESPACE = "py-k8s-job-scheduler"

K8S_STATUS_MAP = {
    "ready": "READY",
    "active": "ACTIVE",
    "terminating": "TERMINATING",
    "succeeded": "SUCCEEDED",
    "failed": "FAILED",
    "missing": "MISSING",
}


class JobManager:
    DELETE_PROPAGATION_POLICY = "Foreground"

    def __init__(
        self, docker_image, env=None, namespace=K8S_DEFAULT_NAMESPACE, cluster_conf=None
    ):
        self._namespace = namespace
        self._docker_image = docker_image
        self._env = env or {}

        # Init Kubernetes
        self._cluster_conf = cluster_conf or config.load_kube_config()

        self._core_api = client.CoreV1Api(self._cluster_conf)
        self._batch_api = client.BatchV1Api(self._cluster_conf)

    def init(self):
        # Create namespace if not exists

        try:
            self._core_api.read_namespace_status(self._namespace)
        except ApiException as e:
            if e.status != 404:
                raise e

            namespace_metadata = client.V1ObjectMeta(name=self._namespace)
            self._core_api.create_namespace(
                client.V1Namespace(metadata=namespace_metadata)
            )
            log.info(f"Created namespace {self._namespace}.")

        return self._namespace

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *args):
        pass

    def list_pods(self, job_name=None):
        ret = self._core_api.list_namespaced_pod(
            namespace=self._namespace,
            label_selector=f"job-name={job_name}" if job_name else "",
        )

        # for i in ret.items:
        #     print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
        #
        return [i.metadata.name for i in ret.items]

    def delete_pod(self, pod_name):
        api_response = self._core_api.delete_namespaced_pod(
            pod_name,
            namespace=self._namespace,
            body=client.V1DeleteOptions(
                grace_period_seconds=2,
                propagation_policy=self.DELETE_PROPAGATION_POLICY,
            ),
        )

        return api_response

    def list_jobs(self):
        ret = self._batch_api.list_namespaced_job(namespace=self._namespace)

        return [i.metadata.name for i in ret.items]

    def job_status(self, job_name):
        api_response = self._batch_api.read_namespaced_job_status(
            job_name, self._namespace
        )

        if api_response.status.ready:
            return K8S_STATUS_MAP["ready"], None
        elif api_response.status.terminating:
            return K8S_STATUS_MAP["terminating"], None
        elif api_response.status.succeeded:
            return K8S_STATUS_MAP["succeeded"], {
                "reason": api_response.status.conditions[0].reason,
                "message": api_response.status.conditions[0].message,
            }
        elif api_response.status.failed:
            return K8S_STATUS_MAP["failed"], {
                "reason": api_response.status.conditions[0].reason,
                "message": api_response.status.conditions[0].message,
            }
        else:
            print(api_response.status)
            return K8S_STATUS_MAP["missing"], None

    def job_logs(self, job_name):
        # Get pods
        pods = self.list_pods(job_name=job_name)

        all_logs = [
            self._core_api.read_namespaced_pod_log(pod, self._namespace) for pod in pods
        ]

        return (
            all_logs[0]
            if len(all_logs) == 1
            else all_logs
            if len(all_logs) > 1
            else None
        )

    @staticmethod
    def _k8s_fqn(name):
        return name.replace("_", "-")

    def create_instant_job(self, cmd, *args, **kwargs):
        job_name = f"job-kjs-{JobManager._k8s_fqn(cmd)}"
        pod_name = f"pod-kjs-{JobManager._k8s_fqn(cmd)}"

        container = self._gen_container_specs(cmd, *args, **kwargs)

        api_response = self._batch_api.create_namespaced_job(
            namespace=self._namespace,
            body=client.V1Job(
                api_version="batch/v1",
                kind="Job",
                metadata=client.V1ObjectMeta(
                    name=job_name, labels={"job_name": job_name}
                ),
                spec=client.V1JobSpec(
                    backoff_limit=0,
                    template=client.V1JobTemplateSpec(
                        spec=client.V1PodSpec(
                            restart_policy="Never", containers=[container]
                        ),
                        metadata=client.V1ObjectMeta(
                            name=pod_name, labels={"pod_name": pod_name}
                        ),
                    ),
                ),
            ),
        )

        return api_response.metadata.name

    def delete_job(self, job_name):
        api_response = self._batch_api.delete_namespaced_job(
            job_name,
            namespace=self._namespace,
            body=client.V1DeleteOptions(
                grace_period_seconds=2,
                propagation_policy=self.DELETE_PROPAGATION_POLICY,
            ),
        )

        status = json.loads(api_response.status.replace("'", '"'))

        return "succeeded" in status and status["succeeded"] > 0

    def list_scheduled_jobs(self, include_details=False):
        ret = self._batch_api.list_namespaced_cron_job(namespace=self._namespace)

        if include_details:
            return ret.items

        return [i.metadata.name for i in ret.items]

    def scheduled_job_status(self, job_name):
        api_response = self._batch_api.read_namespaced_cron_job_status(
            job_name, self._namespace
        )

        return api_response

    def create_scheduled_job(self, schedule, cmd, *args, **kwargs):
        job_name = f"job-kjs-{JobManager._k8s_fqn(cmd)}"
        pod_name = f"pod-kjs-{JobManager._k8s_fqn(cmd)}"

        container = self._gen_container_specs(cmd, *args, **kwargs)

        api_response = self._batch_api.create_namespaced_cron_job(
            namespace=self._namespace,
            body=client.V1CronJob(
                api_version="batch/v1",
                kind="CronJob",
                metadata=client.V1ObjectMeta(
                    name=job_name, labels={"job_name": job_name}
                ),
                spec=client.V1CronJobSpec(
                    schedule=schedule,
                    job_template=client.V1JobTemplateSpec(
                        spec=client.V1JobSpec(
                            template=client.V1PodTemplateSpec(
                                spec=client.V1PodSpec(
                                    restart_policy="Never", containers=[container]
                                ),
                            ),
                        ),
                        metadata=client.V1ObjectMeta(
                            name=pod_name, labels={"pod_name": pod_name}
                        ),
                    ),
                ),
            ),
        )

        return api_response.metadata.name

    def delete_scheduled_job(self, job_name):
        self._batch_api.delete_namespaced_cron_job(
            job_name,
            namespace=self._namespace,
            body=client.V1DeleteOptions(
                grace_period_seconds=2,
                propagation_policy=self.DELETE_PROPAGATION_POLICY,
            ),
        )

        return True

    def _gen_container_specs(self, cmd, *args, **kwargs):
        args_arr = [f"{a}" for a in args] + [f"--{k}={v}" for k, v in kwargs.items()]
        container_name = f"cont-kjs-{JobManager._k8s_fqn(cmd)}"

        # Create container
        container = client.V1Container(
            image=self._docker_image,
            name=container_name,
            image_pull_policy="IfNotPresent",  # Always / Never / IfNotPresent
            command=[cmd],
            args=args_arr,
            env=[client.V1EnvVar(name=k, value=v) for k, v in self._env.items()],
        )

        logging.info(
            f"Created container with name: {container.name}, "
            f"image: {container.image} and args: {container.args}"
        )

        return container
