import psycopg2
import datetime
import os

def nonceCleanup(sqlIpAddr="127.0.0.1"):
    try:
        if sqlIpAddr == "":
            sqlIpAddr = "postgresql"

        print(f"POSTGRESQL connect to {sqlIpAddr}")
        conn = psycopg2.connect(
            host=sqlIpAddr,
            database="chirpstack_ns",
            user="chirpstack_ns",
            password="chirpstack_ns")

        cur = conn.cursor()
        print("POSTGRESQL connection established")
        cur.execute(f"delete from public.device_activation")
        print("POSTGRESQL query executed")
        cur.close()
    except Exception as e:
        print("POSTGRESQL ERROR: " + str(e))
    finally:
        if conn is not None:
            conn.close()
            print("POSTGRESQL connection closed")

