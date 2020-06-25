from threading import Lock
try:
    from opentelemetry import trace
    from opentelemetry.instrumentation.utils import http_status_to_canonical_code
    HAS_OPENTELEMETRY_INSTALLED = True
except (ImportError, ModuleNotFoundError):
    HAS_OPENTELEMETRY_INSTALLED = False

from google.cloud.spanner_v1.gapic import spanner_client
from contextlib import contextmanager
from google.api_core.exceptions import GoogleAPICallError
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

@contextmanager
def trace_call(name, session, extra_attributes=None):
    if not HAS_OPENTELEMETRY_INSTALLED:
        yield None
        return

    tracer = trace.get_tracer(__name__)

    attributes = {
        "db.type": "spanner",
        "db.url": spanner_client.SpannerClient.SERVICE_ADDRESS,
        "db.instance": session._database.name,
        "net.host.name": spanner_client.SpannerClient.SERVICE_ADDRESS
    }

    if extra_attributes:
        attributes.update(extra_attributes)

    with tracer.start_as_current_span(name, kind=trace.SpanKind.CLIENT, attributes=attributes) as span:
        try:
            yield span
        except GoogleAPICallError as error:
            span.set_status(http_status_to_canonical_code(error.code))
            raise
