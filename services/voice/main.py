"""voice: long-lived WebSocket endpoints under /ws/*. Uses Redis (call counter) and Postgres (log)."""
import asyncio
import os
import time

import psycopg
import redis
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

def pg():
    return psycopg.connect(
        host=os.environ["DB_HOST"], port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], connect_timeout=5, autocommit=True,
    )


def rds():
    return redis.Redis(host=os.environ["REDIS_HOST"], port=int(os.getenv("REDIS_PORT", "6379")),
                       socket_connect_timeout=5, decode_responses=True)


def wait_and_init(name):
    """Retry until Postgres and Redis answer, then create tables if missing."""
    for attempt in range(30):
        try:
            with pg() as c:
                c.execute("CREATE TABLE IF NOT EXISTS heartbeats (id serial PRIMARY KEY, source text, at timestamptz DEFAULT now())")
                c.execute("CREATE TABLE IF NOT EXISTS jobs_done (id serial PRIMARY KEY, payload text, at timestamptz DEFAULT now())")
            rds().ping()
            return
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] waiting for dependencies ({attempt}): {e}", flush=True)
            time.sleep(5)
    raise SystemExit("dependencies never became ready")


app = FastAPI(title="jazzai-concierge-test voice")


@app.on_event("startup")
def startup():
    wait_and_init("voice")


@app.get("/health")
def health():
    return {"ok": True, "service": "voice"}


def start_call():
    rds().incr("calls_started")
    with pg() as c:
        c.execute("INSERT INTO heartbeats (source) VALUES ('voice-call')")


@app.websocket("/ws/echo")
async def echo(ws: WebSocket):
    await ws.accept()
    start_call()
    try:
        while True:
            await ws.send_text("echo: " + await ws.receive_text())
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/hold")
async def hold(ws: WebSocket, seconds: int = 300):
    """Keep a 'call' open for N seconds, ticking every 10s (CloudFront timeout test)."""
    await ws.accept()
    start_call()
    try:
        for i in range(0, seconds, 10):
            await ws.send_text(f"tick {i}s")
            await asyncio.sleep(10)
        await ws.send_text("done")
        await ws.close()
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
