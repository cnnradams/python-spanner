from threading import Lock
from opentelemetry import trace
from google.cloud.spanner_v1.gapic import spanner_client
_meter = None
def set_meter(meter):
    global _meter
    _meter = meter

def get_meter():
    return _meter

_unique_pool_id = 0
pool_lock = Lock()
def get_unique_pool_id():
    global _unique_pool_id
    with pool_lock:
        _unique_pool_id += 1
        return _unique_pool_id

tracer = trace.get_tracer(__name__)

def trace_call(name, session):
    attributes = {
        "db.type": "spanner",
        "db.url": spanner_client.SpannerClient.SERVICE_ADDRESS
    }
    return tracer.start_as_current_span(name, kind=trace.SpanKind.CLIENT, attributes=attributes)
