"""FastAPI wiring: one WebSocket, tiny REST, and the composition root.

api/ is the ONLY package that constructs services — everything else receives
its collaborators. app.create_app() is the factory (uvicorn --factory), the
lifespan is the boot order, and docs/event-protocol.md is the contract the
/ws endpoint honors frame by frame.
"""
