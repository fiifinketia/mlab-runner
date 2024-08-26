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

from runner.billing import BillingCronService
from runner.pinggy_helper import PinggyHelperSever
from runner.settings import settings
from runner.main import Runner



async def serve():
    """
    Asynchronously serve the Runner gRPC server.

    This function starts the gRPC server, sets up the necessary services, and handles the server's lifecycle.
    It also starts the billing cron service and the pinggy server if enabled in the settings.
    If the tcp port is being xposed using tcp then the use_pinggy_server should be true to enble the pinggy server

    Returns:
    None
    """
    server_opt = [('grpc.max_send_message_length', 512 * 1024 * 1024), ('grpc.max_receive_message_length', 512 * 1024 * 1024)]
    server: grpc.aio.Server = grpc.aio.server(maximum_concurrent_rpcs=settings.workers_count, options=server_opt)
    runner_pb2_grpc.add_RunnerServicer_to_server(Runner(runner_dir=settings.runner_dir), server)
    server.add_insecure_port(settings.rpc_url)
    print(f"Runner server started on {settings.rpc_url}")
    try:
        await server.start()
        from threading import Thread
        billing_cron = BillingCronService()
        billing_thread = Thread(target=billing_cron.start)
        billing_thread.start()
        if settings.use_pinggy_server:
            pinggy_service = PinggyHelperSever()
            pinggy_thread = Thread(target=pinggy_service.start_server)
            pinggy_thread.start()
        await server.wait_for_termination()
    except InterruptedError:
        pass
    finally:
        billing_cron.stop()
        await server.stop(0)

if __name__ == '__main__':
    asyncio.run(serve())
