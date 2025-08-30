from datetime import datetime, timezone
import requests
from typing import Dict

from .constants import HEADER_DATE_FMT
from .signature import get_request_signature
from .workflow_request import WorkflowTriggerRequest
from .workflow_trigger_bulk import BulkWorkflowTrigger


class WorkflowsApi:
    def __init__(self, config):
        self.config = config
        self.metadata = {"User-Agent": self.config.user_agent}

    def __get_headers(self):
        return {
            "Content-Type": "application/json; charset=utf-8",
            "Date": datetime.now(timezone.utc).strftime(HEADER_DATE_FMT),
            "User-Agent": self.config.user_agent,
        }

    def trigger(self, workflow: WorkflowTriggerRequest) -> Dict:
        workflow_body, body_size = workflow.get_final_json(self.config, is_part_of_bulk=False)
        try:
            headers = self.__get_headers()
            url = "{}trigger/".format(self.config.base_url)
            # Signature and Authorization-header
            content_txt, sig = get_request_signature(url, 'POST', workflow_body,
                                                     headers, self.config.workspace_secret)
            headers["Authorization"] = "{}:{}".format(self.config.workspace_key, sig)
            # -----
            resp = requests.post(url, data=content_txt.encode('utf-8'), headers=headers)
        except Exception as ex:
            error_str = ex.__str__()
            return {
                "success": False,
                "status": "fail",
                "status_code": 500,
                "message": error_str,
                "raw_response": None,
            }
        else:
            ok_response = resp.status_code // 100 == 2
            try:
                resp_json = resp.json()
            except ValueError:
                resp_json = None
            if ok_response:
                return {
                    "success": True,
                    "status": "success",
                    "status_code": resp.status_code,
                    "message": resp_json.get("message_id") if resp_json else resp.text,
                    "raw_response": resp_json,
                }
            else:
                return {
                    "success": False,
                    "status": "fail",
                    "status_code": resp.status_code,
                    "message": resp_json.get("error", {}).get("message") if resp_json else resp.text,
                    "raw_response": resp_json,
                }

    def bulk_trigger_instance(self):
        """
        USAGE:
        supr_client = Suprsend("__workspace_key__", "__workspace_secret__")
        bulk_ins = supr_client.workflows.bulk_trigger_instance()

        # append one by one
        for i in range(0, 10):
            w = WorkflowTriggerRequest(body) # Workflow instance
            bulk_ins.append(w)

        # append many in one call
        all_workflows = [W1, W2, ...] # multiple workflows
        bulk_ins.append(*all_workflows)

        # call trigger
        response = bulk_ins.trigger()

        :return:
        """
        return BulkWorkflowTrigger(self.config)
