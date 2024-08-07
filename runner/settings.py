"""Settings for the application."""
import enum
import os
from pathlib import Path
from tempfile import gettempdir
from typing import Optional
from dotenv import load_dotenv

from pydantic import BaseSettings
from yarl import URL

TEMP_DIR = Path(gettempdir())
load_dotenv(override=True)

class LogLevel(str, enum.Enum):  # noqa: WPS600
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class Settings(BaseSettings):
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    host: str = os.getenv("HOST", "localhost")
    rpc_port: int = int(os.getenv("RPC_PORT", "50051"))
    monitor_port: int = int(os.getenv("MONITOR_PORT", "50051"))
    # quantity of workers for uvicorn, get from env
    workers_count: int = int(os.getenv("WORKERS_COUNT", "1"))
    # Enable uvicorn reloading

    # Variables for the GitHub API
    gitlab_url: str = os.getenv("GITLAB_URL", "")
    gitlab_server: str = os.getenv("GITLAB_SERVER", "")
    gitlab_token: str = os.getenv("GITLAB_TOKEN", "")
    # git_user_path: str = "/var/lib/git"

    cog_base_dir = os.getenv("COG_BASE_DIR", "/var/lib/docker/volumes/filez")

    results_dir: str = os.getenv("RESULTS_DIR", "/var/lib/docker/volumes/filez/results")
    server_base_dir: str = os.getenv("SERVER_BASE_DIR", "/var/lib/docker/volumes/filez/server")
    runner_dir: str = os.getenv("RUNNER_BASE_DIR", "/var/lib/docker/volumes/filez/runner")
    # datasets_dir: str = git_user_path + "/datasets"
    # models_dir: str = git_user_path + "/models"

    # sudo_password: str = os.getenv("SUDO_PASSWORD", "")

    @property
    def rpc_url(self):
        """
        Construct the RPC URL.

        :return: RPC URL.
        """
        return URL.build(scheme="grpc", host=self.host, port=self.rpc_port)


    class Config:
        """Configuration for settings."""
        env_file = ".env"
        env_prefix = "SERVER_"
        env_file_encoding = "utf-8"


settings = Settings()
