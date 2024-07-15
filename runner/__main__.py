import asyncio
import grpc
from mlab_pyprotos import runner_pb2_grpc 
from runner.settings import settings
from runner.runner import Runner
import logging

logging.basicConfig(level=logging.DEBUG)
async def serve():
    logger = logging.getLogger(__name__)
    server: grpc.aio.Server = grpc.aio.server(maximum_concurrent_rpcs=settings.workers_count)
    runner_pb2_grpc.add_RunnerServicer_to_server(Runner(runner_dir=settings.runner_dir), server)
    server.add_insecure_port('0.0.0.0:50051')
    logger.info('Runner server started on port 50051')
    try:
        await server.start()
        await server.wait_for_termination()
    except InterruptedError:
        pass
    finally:
        await server.stop(0)

if __name__ == '__main__':
    asyncio.run(serve())