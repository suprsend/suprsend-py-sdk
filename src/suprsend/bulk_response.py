
class BulkResponse:
    def __init__(self):
        self.status = None
        self.failed_records = []
        self.total = 0
        self.success = 0
        self.failure = 0
        self.warnings = []

    def __str__(self):
        return f"BulkResponse<status: {self.status} | total: {self.total} | success: {self.success} | " \
               f"failure: {self.failure} | warnings: {len(self.warnings)}>"

    def merge_chunk_response(self, ch_resp):
        if not ch_resp:
            return
        # possible status: success/partial/fail
        if self.status is None:
            self.status = ch_resp["status"]
        else:
            if ch_resp["status"] == "partial":
                self.status = "partial"
            elif self.status == "success":
                if ch_resp["status"] == "fail":
                    self.status = "partial"
            elif self.status == "fail":
                if ch_resp["status"] == "success":
                    self.status = "partial"
        self.total += ch_resp.get("total", 0)
        self.success += ch_resp.get("success", 0)
        self.failure += ch_resp.get("failure", 0)
        failed_recs = ch_resp.get("failed_records", [])
        self.failed_records.extend(failed_recs)

    @classmethod
    def empty_chunk_success_response(cls):
        return {
            "status": "success",
            "status_code": 200,
            "total": 0,
            "success": 0,
            "failure": 0,
            "failed_records": [],
            "raw_response": None,
        }

    @classmethod
    def invalid_records_chunk_response(cls, invalid_records):
        return {
            "status": "fail",
            "status_code": 500,
            "total": len(invalid_records),
            "success": 0,
            "failure": len(invalid_records),
            "failed_records": invalid_records,
            "raw_response": None,
        }

    @classmethod
    def parse_bulk_api_v2_response(cls, resp_json: dict):
        total_count = len(resp_json["records"])
        success_count = sum([1 for _ in resp_json["records"] if _["status"] == "success"])
        failure_count = total_count - success_count
        return {
            "status": ("partial" if success_count > 0 else "fail") if failure_count > 0 else "success",
            "total": total_count,
            "success": success_count,
            "failure": failure_count,
            "records": resp_json["records"],
        }
