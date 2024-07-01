import asyncio
from concurrent import futures
import sys
import grpc
import requests
from runner import runner_pb2_grpc, runner_pb2 
from runner.settings import settings
import runner.cog as cg

import inspect
import time
import multiprocessing
import logging

logging.basicConfig(level=logging.INFO)

def add_timeout(function, limit=60):
    assert inspect.isfunction(function)
    if limit <= 0:
        raise ValueError()
    return _Timeout(function, limit)

class _Timeout:
    def __init__(self, function, limit):
        self.__limit = limit
        self.__function = function
        self.__timeout = time.clock()
        self.__process = multiprocessing.Process()
        self.__queue = multiprocessing.Queue()

    def __call__(self, *args, **kwargs):
        self.__process = multiprocessing.Process(
            target=_target,
            args=(self.__queue, self.__function) + args,
            kwargs=kwargs
        )
        self.__process.start()
        self.__process.join(self.__limit)
        if self.__process.is_alive():
            self.__process.terminate()
            raise TimeoutError("Function execution timed out")
        success, result = self.__queue.get()
        if success:
            return result
        else:
            raise result

def _target(queue, function, *args, **kwargs):
    try:
        queue.put((True, function(*args, **kwargs)))
    except:
        queue.put((False, sys.exc_info()[1]))


class Runner(runner_pb2_grpc.RunnerServicer):
    _server_monitor_url = 'http://197.255.122.208:61208/api/4/all'
    def get_runner(self, request, context):
        server_status = self._get_server_status()
        return runner_pb2.GetRunnerResponse(status=server_status)
    
    def stop_task(self, request, context):
        return super().stop_task(request, context)
    
    def remove_task(self, request, context):
        return super().remove_task(request, context)
    
    def create_task_environment(self, request, context):
        asyncio.run(cg.setup(request.job_id, request.dataset_name, request.model_name, request.dataset_branch, request.model_branch))
        return runner_pb2.CreateTaskResponse(status="success")
    
    def get_task_environment(self, request, context):
        return super().get_task_environment(request, context)
    
    def run_task(self, request, context):
        return super().run_task(request, context)
    
    def _get_server_status(self):
        # res = requests.get(self._server_monitor_url)
        # print(res.json())
        # TODO: Function to calculate availability
        return "available"
    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=settings.workers_count))
    runner_pb2_grpc.add_RunnerServicer_to_server(Runner(), server)
    server.add_insecure_port('0.0.0.0:50051')
    server.start()
    print('Runner server started on port 50051')
    server.wait_for_termination()

    # while not is_out:
    #     print('Runner server stopped')

if __name__ == '__main__':
    serve()