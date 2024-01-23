import psycopg2
import telnetlib


def sqlCleanup(sqlIpAddr="127.0.0.1", verbose=False):    
    # SQL database cleanup (delete nonces)
    try:
        if sqlIpAddr == "":
            sqlIpAddr = "postgresql"
        if verbose:
            print(f"POSTGRESQL connect to {sqlIpAddr}")
        conn = psycopg2.connect(
            host=sqlIpAddr,
            database="chirpstack_ns",
            user="chirpstack_ns",
            password="chirpstack_ns")

        cur = conn.cursor()
        if verbose:
            print("POSTGRESQL connection established")

        cur.execute(f"delete from public.device_activation")
        #cur.execute(f"delete from public.device_queue")
        conn.commit()

        if verbose:
            print("POSTGRESQL query executed")
        cur.close()
    except Exception as e:
        print("POSTGRESQL ERROR: " + str(e))
    finally:
        if conn is not None:
            conn.close()
            if verbose:
                print("POSTGRESQL connection closed")


def redisCleanup():
    host = "172.31.255.102"
    port = 6379
    telnet = telnetlib.Telnet(host, port)
    telnet.write("flushdb\n".encode('ascii'))
    telnet.close()