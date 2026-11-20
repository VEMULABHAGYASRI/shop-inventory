"""Business logic. Services take a database Session and plain values, and
raise exceptions from app.errors. They never import FastAPI, so they can be
reused from the CLI, scripts, or tests."""
