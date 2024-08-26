import base64
import logging
from pathlib import Path
import pickle
import subprocess
import time

import runner.cog as cg
from mlab_pyprotos import runner_pb2, runner_pb2_grpc

class RunnerException(Exception):
    def __init__(self, message: str) -> None:
        """
        Initialize a new instance of RunnerException.

        Parameters:
        message (str): The error message to be associated with this exception.

        Returns:
        None: This method does not return any value. It initializes the exception instance.
        """
        super().__init__(message)
        self.message = message
        self._logger = logging.getLogger(__name__)

class Runner(runner_pb2_grpc.RunnerServicer):

    
    def __init__(self, workers_count: int=5, runner_dir: str = "") -> None:
        """
        Initialize a new instance of Runner class.

        This class is responsible for managing task environments and running tasks.
        It also handles worker count management and communication with external services.

        Parameters:
        workers_count (int, optional): The initial number of worker processes. Defaults to 5.
        runner_dir (str, optional): The directory where runner related files are stored. Defaults to an empty string.

        Returns:
        None: This method does not return any value. It initializes the Runner instance.
        """
        super().__init__()
        self.save_worker_count(workers_count)
        self.runner_dir = runner_dir

    
        @staticmethod
        def logger():
            """
            This method initializes and returns a logger instance for the Runner class.

            The logger is configured to log messages at the INFO level. It logs a message
            indicating that the Runner server is starting.

            Parameters:
            None

            Returns:
            _logger (logging.Logger): A logger instance configured for the Runner class.
            """
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
        """
        Runs a task on the specified job.

        This function prepares the environment for the task, runs the task, and fetches the results.
        It decrements the worker count before running the task and increments it after the task is completed.

        Parameters:
        request (runner_pb2.RunTaskRequest): A request containing the necessary information to run the task, such as the job ID, dataset name, model name, task name, task ID, user ID, and trained model.
        context (grpc.aio.Context): The context object provided by the gRPC framework.

        Returns:
        generator: A generator that yields `runner_pb2.RunTaskResponse` objects containing the task's output.

        Raises:
        RunnerException: If there are not enough workers to create a task environment.
        """
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
        """
        Get the current server status based on the available worker count.

        This function calculates the server status by checking the number of available worker processes.
        If the worker count is greater than 0, the server status is set to "available". Otherwise, it is set to "occupied".

        Parameters:
        self (Runner): The instance of the Runner class.

        Returns:
        str: The server status, either "available" or "occupied".
        """
        # TODO: Function to calculate availability
        workers_count = self.load_worker_count()
        Runner.logger().debug(f"Current worker count: {workers_count} workers")
        return "available" if workers_count > 0 else "occupied"
    
    def _stream_process(self, process):
        """
        Check if the given process is still running.

        This function uses the `poll()` method of the subprocess.Popen object to determine if the process is still running.
        If the process is still running, `poll()` returns None. Otherwise, it returns an exit code.

        Parameters:
        process (subprocess.Popen): The subprocess.Popen object representing the process to be checked.

        Returns:
        bool: True if the process is still running, False otherwise.
        """
        go = process.poll() is None
        return go
