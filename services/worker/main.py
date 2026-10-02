"""worker: pops jobs from the Redis list "jobs" and records them in Postgres."""
import os
import time

import psycopg
import redis

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


if __name__ == "__main__":
    wait_and_init("worker")
    r = rds()
    print("[worker] started", flush=True)
    while True:
        item = r.blpop("jobs", timeout=10)
        if item:
            with pg() as c:
                c.execute("INSERT INTO jobs_done (payload) VALUES (%s)", (item[1],))
            print(f"[worker] done {item[1]}", flush=True)
