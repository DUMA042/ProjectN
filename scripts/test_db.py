import psycopg2

def test_conn(user, pwd):
    try:
        conn = psycopg2.connect(dbname="postgres", user=user, password=pwd, host="localhost", port="5432")
        print(f"SUCCESS: user={user}, password={pwd}")
        conn.close()
        return True
    except Exception as e:
        print(f"FAIL: user={user}, password={pwd} - {str(e).strip()}")
        return False

# Try combinations since "1234" on "postgres" failed
combos = [
    ("postgres", "1234"),
    ("HP", "1234"),
    ("admin", "1234"),
    ("root", "1234"),
    ("postgres", "postgres"),
    ("postgres", "")
]

for u, p in combos:
    if test_conn(u, p):
        break
