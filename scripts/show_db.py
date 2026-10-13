import os, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from vasool import crypto
from vasool.store import DEFAULT_DB

DECRYPT = "--decrypt" in sys.argv
db = os.getenv("VASOOL_DB", DEFAULT_DB)
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row

def cut(s, n=90):
    s = str(s)
    return s if len(s) <= n else s[:n] + "..."

print(f"\nDATABASE  {db}")
print(f"KEY FILE  {crypto.key_path()}  (exists: {crypto.key_path().exists()})   -- key is NOT inside the database\n")

print("TABLES")
for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    print(f"  {name:<14}{n:>5} rows")

print("\nUSERS  (what a thief would get)")
for r in con.execute("SELECT login, name, salt, pw_hash FROM users"):
    print(f"  login    {r['login']}")
    print(f"  name     {cut(r['name'], 60)}" + (f"   -> {crypto.open_(r['name'])}" if DECRYPT else ""))
    print(f"  salt     {r['salt']}")
    print(f"  pw_hash  {r['pw_hash']}   (PBKDF2-HMAC-SHA256 x {crypto.PBKDF2_ITERATIONS:,} -- the password itself is never stored)\n")

print("ACCOUNTS")
for r in con.execute("SELECT id, user_id, profile, transactions FROM accounts ORDER BY updated_at DESC LIMIT 3"):
    print(f"  {r['id']}   owner {r['user_id']}")
    print(f"    profile       {cut(r['profile'])}")
    print(f"    transactions  {cut(r['transactions'])}")
    if DECRYPT:
        p = crypto.open_(r["profile"])
        t = crypto.open_(r["transactions"])
        print(f"    -> decrypted  {p.get('holder_name')} | {p.get('bank')} | {len(t)} lines | first: {t[0]['date']} {cut(t[0]['narration'], 40)} Rs {t[0]['debit'] or t[0]['credit']}")
    print()

print("FINDINGS")
for r in con.execute("SELECT id, account_id, doc FROM findings LIMIT 3"):
    print(f"  {r['id']}  {cut(r['doc'], 80)}" + (f"\n    -> {crypto.open_(r['doc'])['rule_id']} Rs {crypto.open_(r['doc'])['amount']}" if DECRYPT else ""))

print("\nSESSIONS   tokens hidden -- HttpOnly cookie, random 32 bytes, 7-day expiry")
print(f"  {con.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]} active")
if not DECRYPT:
    print("\nRun again with --decrypt to open the same rows with the key file.")