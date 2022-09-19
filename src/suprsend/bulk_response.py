
class BulkResponse:
    def __init__(self):
        self.status = None
        self.failed_records = []
        self.total = 0
        self.success = 0
        self.failure = 0
        self.warnings = []

    def __str__(self):
        return f"BulkResponse<status:{self.status}| total: {self.total} | success: {self.success} | " \
               f"failure: {self.failure} | warnings: {len(self.warnings)}>"

    def merge_chunk_response(self, ch_resp):
        if not ch_resp:
            return
        # possible status: success/partial/fail
        if self.status is None:
            self.status = ch_resp["status"]
        else:
            if self.status == "success":
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
