"""web: HTTP API behind CloudFront/ALB. Uses Postgres and Redis."""
import os
import time

import psycopg
import redis
import uvicorn
from fastapi import FastAPI

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


app = FastAPI(title="jazzai-concierge-test web")


@app.on_event("startup")
def startup():
    wait_and_init("web")


@app.get("/health")
def health():
    return {"ok": True, "service": "web"}


@app.get("/")
def root():
    return {"service": "jazzai-concierge-test updated", "app": "web"}


@app.get("/db")
def db():
    with pg() as c:
        return {"postgres": c.execute("select version()").fetchone()[0]}


@app.get("/redis")
def redis_check():
    return {"redis_ping": rds().ping(), "hits": rds().incr("hits")}


@app.get("/status")
def status():
    """Shows the scheduler -> Redis -> worker -> Postgres loop is alive."""
    with pg() as c:
        hb = c.execute("select count(*) from heartbeats where source='scheduler'").fetchone()[0]
        jd = c.execute("select count(*) from jobs_done").fetchone()[0]
    return {"scheduler_heartbeats": hb, "jobs_done_by_worker": jd, "queue_length": rds().llen("jobs")}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
