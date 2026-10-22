import os
from fastapi import FastAPI
from opentelemetry import trace

MODE = os.getenv("MODE", "none")        # none | noexport | otlp
SPANS = int(os.getenv("SPANS", "10"))   # spans per request

if MODE != "none":
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    provider = TracerProvider()
    if MODE == "otlp":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(endpoint="http://collector:4317", insecure=True)))
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer("overhead-demo")
app = FastAPI()

def busy():
    return sum(i * i for i in range(2000))

def work(depth):
    return work(depth - 1) if depth > 1 else busy()

def work_traced(depth):
    with tracer.start_as_current_span("work"):
        return work_traced(depth - 1) if depth > 1 else busy()

@app.get("/work")
def endpoint():
    return {"result": (work if MODE == "none" else work_traced)(SPANS)}