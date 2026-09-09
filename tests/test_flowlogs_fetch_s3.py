import gzip
import io
import boto3
from botocore.stub import Stubber
from botocore.response import StreamingBody
from inflight.flowlogs import fetch_s3


def _gz(text: str):
    raw = gzip.compress(text.encode("utf-8"))
    return StreamingBody(io.BytesIO(raw), len(raw))


def test_fetch_s3_gunzips_lines():
    s3 = boto3.client("s3", region_name="us-east-1",
                      aws_access_key_id="x", aws_secret_access_key="x")
    stub = Stubber(s3)
    stub.add_response("list_objects_v2", {"Contents": [{"Key": "flow/1.gz"}]})
    body = "line-a\nline-b\n"
    stub.add_response("get_object", {"Body": _gz(body)})
    stub.activate()

    class Sess:
        def client(self, _n): return s3

    assert fetch_s3(Sess(), "bkt", "flow/", 1000, 2000) == ["line-a", "line-b"]
