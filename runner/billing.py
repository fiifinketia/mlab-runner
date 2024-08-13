
from enum import Enum
import time
from typing import Any

from pydantic import BaseModel
from glances.main import GlancesMain
from glances.stats import GlancesStats
import requests
import schedule

from runner.settings import settings


class Action(str, Enum):
    """Action model."""
    CREATE_DATASET = "create:dataset"
    CREATE_MODEL = "create:model"
    CREATE_JOB = "create:job"
    STOP_JOB = "stop:job"
    CLOSE_JOB = "close:job"
    RUN_JOB = "run:job"
    UPLOAD_TEST_JOB = "upload:test:job"
    RUNNER_BILL = "runner:bill"

class BalanceBillDTO(BaseModel):
    """DTO for balance bill."""
    action: Action
    data: Any

class CheckBillDTO(BaseModel):
    """Check bill model."""
    action: Action
    data: Any

class BillingCronService:
    def __init__(self):
        self.mlab_api = f"{settings.mapi_url}/api/billings/check"
        glances = GlancesMain()
        self._server_stats = GlancesStats(config=glances.get_config(), args=glances.get_args())
        print("Billings service initializing...")
        schedule.every(0.5).minutes.do(self._submit_billing)
    
    def start(self):
        while 1:
            schedule.run_pending()
            time.sleep(0.1)

    def stop(self):
        schedule.clear()
    def _get_server_stats(self):
        self._server_stats.update()
        return self._server_stats.getAllViewsAsDict()

    def _submit_billing(self):
        body = CheckBillDTO(
            action=Action.RUNNER_BILL,
            data=self._get_server_stats()
        )
        try:
            res = requests.post(self.mlab_api, data=body.json(), timeout=20, headers={"x-api-key": settings.mapi_api_key}, verify=False)
            res.raise_for_status()
            print("Billing update sent to server")
        except Exception as e:
            print(f"Error sending billing update to server: {e}")