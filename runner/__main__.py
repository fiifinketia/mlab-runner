import argparse
import asyncio
import grpc

import base64
import logging
from pathlib import Path
import pickle
import subprocess
import time
from mlab_pyprotos import runner_pb2, runner_pb2_grpc

import runner.cog as cg
from runner.billing import BillingCronService
from runner.pinggy_helper import PinggyHelperSever
from runner.settings import settings

class RunnerException(Exception):

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
        self._logger = logging.getLogger(__name__)



class Runner(runner_pb2_grpc.RunnerServicer):

    def __init__(self, workers_count: int=5, runner_dir: str = "") -> None:
        super().__init__()
        self.save_worker_count(workers_count)
        self.runner_dir = runner_dir

    @staticmethod
    def logger():
        _logger = logging.getLogger(__name__)
        _logger.info('Starting')
        return _logger

    @staticmethod
    def save_worker_count(count) -> None:
        file_path = Path(f"{settings.runner_dir}/worker_count.pkl")
        with open(file_path, 'wb') as f:
            pickle.dump(count, f)
    
    @staticmethod
    def load_worker_count() -> int:
        file_path = Path(f"{settings.runner_dir}/worker_count.pkl")
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return 0
    
    @staticmethod
    def decrement_worker_count() -> int:
        workers_count = Runner.load_worker_count()
        workers_count = workers_count -1
        Runner.save_worker_count(workers_count)
        Runner.logger().debug(f"Worker count decrease: {workers_count}")
        return workers_count
    
    @staticmethod
    def increment_worker_count() -> int:
        workers_count = Runner.load_worker_count()
        workers_count = workers_count +1
        Runner.save_worker_count(workers_count)
        Runner.logger().debug(f"Worker count increase: {workers_count}")
        return workers_count
    
    @staticmethod
    def check_worker_count() -> bool:
        worker_count = Runner.load_worker_count()
        if worker_count < 0:
            Runner.logger().error("Not enough workers to create a task environment")
            raise RunnerException("Not enough workers to create a task environment")
        return True
    def get_runner(self, request, context):
        server_status = self._get_server_status()
        return runner_pb2.GetRunnerResponse(status=server_status)
    
    def stop_task(self, request, context):
        cg.stop(request.job_id)
        return runner_pb2.StopTaskResponse()
    
    def remove_task_environment(self, request, context):
        cg.remove(request.job_id)
        return runner_pb2.RemoveTaskResponse()
    
    async def create_task_environment(self, request, context):
        self.check_worker_count()
        
        await cg.setup(request.job_id, request.dataset.name, request.model.name, request.dataset.branch, request.model.branch)
        Runner.increment_worker_count()
        return runner_pb2.CreateTaskResponse()
    
    def get_task_environment(self, request, context):
        return super().get_task_environment(request, context)
    
    async def run_task(self, request, context):
        self.check_worker_count()
        Runner.decrement_worker_count()
        await cg.prepare(job_id=request.job_id, dataset_name=request.dataset.name, model_name=request.model.name, dataset_type=request.dataset.type, dataset_branch=request.dataset.branch, model_branch=request.model.branch, results_dir=request.results_dir)
        process: subprocess.Popen[bytes] = cg.run(name=request.task_name, model_name=request.model.name, dataset_name=request.dataset.name, task_id=request.task_id, user_id=request.user_id, job_id=request.job_id, trained_model=request.trained_model)
        while self._stream_process(process):
            for line in process.stdout:
                yield runner_pb2.RunTaskResponse(line=line)
            time.sleep(0.1)
        Runner.logger().info("Task completed successfully")
        results = cg.fetch_results(request.job_id, request.model.name)
        if results is None:
            Runner.logger().error("No results")
        elif results[0] == "success":
            status, success = results
            Runner.logger().info("Results fetched successfully")
            files = []
            for key, value in success.get("files").items():
                info = runner_pb2.FileInfo(
                    name=key,
                    extension=key.split(".")[-1]
                )
                bytz = base64.b64decode(value)
                bytes_content = runner_pb2.BytesContent(
                    file_size=len(value),
                    buffer=bytz,
                    info=info,
                )
                files.append(bytes_content)
            metrics = []
            for key, value in success.get("metrics").items():
                metric = runner_pb2.Metrics(
                    name=key,
                    metric=str(value),
                )
                metrics.append(metric)
            task_result = runner_pb2.TaskResult(
                task_id=success.get('task_id'),
                status=status,
                metrics=metrics,
                files=files,
                pkg_name=success.get('pkg_name'),
                pretrained_model=success.get('pretrained_model'),
            )
            yield runner_pb2.RunTaskResponse(result=task_result)
        else:
            Runner.logger().error("Error in return")
            status, error = results
            files = []
            for key, value in error.get("files").items():
                info = runner_pb2.FileInfo(
                    name=key,
                    extension=key.split(".")[-1]
                )
                bytz = base64.b64decode(value)

                bytes_content = runner_pb2.BytesContent(
                    file_size=len(value),
                    buffer=bytz,
                    info=info,
                )
                files.append(bytes_content)
            task_result = runner_pb2.TaskResult(
                task_id=error.get('task_id'),
                status=status,
                files=files,
                pkg_name=error.get('pkg_name'),
            )
            yield runner_pb2.RunTaskResponse(result=task_result)

        Runner.increment_worker_count()       
    
    def _get_server_status(self):
        # TODO: Function to calculate availability
        workers_count = self.load_worker_count()
        Runner.logger().debug(f"Current worker count: {workers_count} workers")
        return "available" if workers_count > 0 else "occupied"
    
    def _stream_process(self, process):
        go = process.poll() is None
        return go



async def serve():
    server_opt = [('grpc.max_send_message_length', 512 * 1024 * 1024), ('grpc.max_receive_message_length', 512 * 1024 * 1024)]
    server: grpc.aio.Server = grpc.aio.server(maximum_concurrent_rpcs=settings.workers_count, options=server_opt)
    runner_pb2_grpc.add_RunnerServicer_to_server(Runner(runner_dir=settings.runner_dir), server)
    server.add_insecure_port(settings.rpc_url)
    print(f"Runner server started on {settings.rpc_url}")
    try:
        await server.start()
        # from threading import Thread
        # thread = Thread()
        billing_cron = BillingCronService()
        asyncio.to_thread(billing_cron.start)
        print(settings.use_pinggy_server)
        if settings.use_pinggy_server:
            pinggy_service = PinggyHelperSever()
            asyncio.to_thread(pinggy_service.start_server)
        await server.wait_for_termination()
    except InterruptedError:
        pass
    finally:
        billing_cron.stop()
        await server.stop(0)

if __name__ == '__main__':
    asyncio.run(serve())
