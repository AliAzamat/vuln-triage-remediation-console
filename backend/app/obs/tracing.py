"""OpenTelemetry-style spans + counters. In prod these export to an OTLP collector
(Grafana/Tempo); here the API is what matters — every pipeline stage is a span, so a
slow or failing stage is visible instead of a mystery inside a black-box worker."""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace, metrics

_tracer = trace.get_tracer("vulntriage")
_meter = metrics.get_meter("vulntriage")

# Counters the console and alerting read: work done and time taken per stage.
findings_triaged = _meter.create_counter("findings_triaged")
scan_duration = _meter.create_histogram("scan_duration_seconds")


@contextmanager
def span(name: str, **attrs) -> Iterator[None]:
    """Wrap a pipeline stage in a span with attributes (scan id, scanner, count).
    Attributes are what let you slice latency by scanner or by repo later."""
    with _tracer.start_as_current_span(name) as sp:
        for k, v in attrs.items():
            sp.set_attribute(k, v)
        start = time.monotonic()
        try:
            yield
        finally:
            sp.set_attribute("duration_s", round(time.monotonic() - start, 3))
