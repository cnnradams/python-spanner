from contextlib import contextmanager
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def trace_call(name, database):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            span = self.tracer.start_span(name, trace.Tracer.CURRENT_SPAN, trace.SpanKind.CLIENT, {})
            fn(*args, **kwargs)
class SpannerTracerManager():

    def __init__(self, name):
        self.tracer = trace.get_tracer(__name__)

    def start_spanner_span_as_current(self, name, session=None):
        
        return self.tracer.use_span(span, end_on_exit=True)