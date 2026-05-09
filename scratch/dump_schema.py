import os
import subprocess
import urllib.parse
from dotenv import load_dotenv

def dump_schema():
    load_dotenv()
    db_url = os.getenv('DATABASE_URL')
    
    # We strip out the +psycopg2 part if present for standard parsing
    if db_url and '+psycopg2' in db_url:
        db_url = db_url.replace('+psycopg2', '')
        
    parsed = urllib.parse.urlparse(db_url)
    
    env = os.environ.copy()
    env['PGPASSWORD'] = parsed.password

    cmd = [
        'pg_dump',
        '-h', parsed.hostname,
        '-p', str(parsed.port),
        '-U', parsed.username,
        '-d', parsed.path.lstrip('/'),
        '-s', # schema only
        '-x', # no privileges (GRANT/REVOKE)
        '-O'  # no owner
    ]

    print(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        # We will save this to a file so it can be easily read or provided to the user.
        out_path = os.path.join(os.getcwd(), 'scratch', 'complete_schema.sql')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        print(f"Schema successfully dumped to {out_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error dumping schema:")
        print(e.stderr)
    except FileNotFoundError:
        print("pg_dump is not available in the system PATH. We will need to use a SQLAlchemy introspection script instead.")

if __name__ == "__main__":
    dump_schema()
