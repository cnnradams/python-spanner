import unittest
import mock
import sys
import time
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider, export
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
import importlib
from google.api_core.exceptions import GoogleAPICallError
from google.cloud.spanner_v1 import metrics

def _make_rpc_error(error_cls, trailing_metadata=None):
    import grpc

    grpc_error = mock.create_autospec(grpc.Call, instance=True)
    grpc_error.trailing_metadata.return_value = trailing_metadata
    return error_cls("error", errors=(grpc_error,))

def _make_session():
    from google.cloud.spanner_v1.session import Session

    return mock.Mock(autospec=Session, instance=True)

class TestNoTracing(unittest.TestCase):
    def setUp(self):
        self._temp_opentelemetry = sys.modules['opentelemetry']

        sys.modules['opentelemetry'] = None

    def tearDown(self):
        sys.modules['opentelemetry'] = self._temp_opentelemetry


    def test_no_trace_call(self):
        importlib.reload(metrics)
        

        with metrics.trace_call("Test", _make_session()) as no_span:
            self.assertIsNone(no_span)

class TestTracing(unittest.TestCase):
    def setUp(self):
        self.original_tracer_provider = trace_api.get_tracer_provider()
        self.tracer_provider = TracerProvider()
        self.memory_exporter = InMemorySpanExporter()
        span_processor = export.SimpleExportSpanProcessor(self.memory_exporter)
        self.tracer_provider.add_span_processor(span_processor)
        trace_api.set_tracer_provider(self.tracer_provider)

    def tearDown(self):
        trace_api.set_tracer_provider(self.original_tracer_provider)

    def test_trace_call(self):
        importlib.reload(metrics)

        extra_attributes = {
            "attribute1": "value1",
            # Since our database is mocked, we have to override the db.instance parameter so it is a string
            "db.instance": "database_name"
        } 

        expected_attributes = {
            "db.type": "spanner",
            "db.url": "spanner.googleapis.com:443",
            "net.host.name": "spanner.googleapis.com:443"
        }
        expected_attributes.update(extra_attributes)

        with metrics.trace_call("CloudSpanner.Test", _make_session(), extra_attributes) as span:
            span.set_attribute("after_setup_attribute", 1)
        
        expected_attributes["after_setup_attribute"] = 1

        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        span = span_list[0]
        self.assertEqual(span.kind, trace_api.SpanKind.CLIENT)
        self.assertEqual(span.attributes, expected_attributes)
        self.assertEqual(span.name, "CloudSpanner.Test")
        self.assertEqual(span.status.canonical_code, trace_api.status.StatusCanonicalCode.OK)
    
    def test_trace_error(self):
        importlib.reload(metrics)

        extra_attributes = {
            "db.instance": "database_name"
        } 

        expected_attributes = {
            "db.type": "spanner",
            "db.url": "spanner.googleapis.com:443",
            "net.host.name": "spanner.googleapis.com:443"
        }
        expected_attributes.update(extra_attributes)

        try:
            with metrics.trace_call("CloudSpanner.Test", _make_session(), extra_attributes) as span:
                from google.api_core.exceptions import InvalidArgument
                raise _make_rpc_error(InvalidArgument)
        except GoogleAPICallError:
            pass

        span_list = self.memory_exporter.get_finished_spans()
        self.assertEqual(len(span_list), 1)
        span = span_list[0]
        self.assertEqual(span.kind, trace_api.SpanKind.CLIENT)
        self.assertEqual(span.attributes, expected_attributes)
        self.assertEqual(span.name, "CloudSpanner.Test")
        self.assertEqual(span.status, trace_api.status.StatusCanonicalCode.INVALID_ARGUMENT)