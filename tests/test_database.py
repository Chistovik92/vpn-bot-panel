import os
import tempfile
from pathlib import Path

def test_database_initializes(monkeypatch):
    from config import Config
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.chdir(tmp)
    from database import Database
    db = Database()
    with db.get_connection() as conn:
        tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert {"users","admins","services","payments","vpn_configs","orders","audit_log"} <= tables
