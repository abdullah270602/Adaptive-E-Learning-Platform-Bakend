"""
Initialize the PostgreSQL schema from DB_schema_sql_scritp.sql.

- Ensures extensions (uuid-ossp, pgcrypto).
- Executes the SQL file statement-by-statement.
- Skips invalid uuid_* C-language function stubs and their ALTER OWNER lines.
- Continues on benign errors (e.g., already exists) and reports a summary.

Env:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE (optional)

Usage:
  python scripts/init_db.py --sql DB_schema_sql_scritp.sql --yes
"""
import argparse
import os
import sys
import textwrap
import psycopg2

EXT_SETUP = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
"""

def split_sql(statements: str):
    """
    Split SQL into individual statements, respecting $$-quoted blocks and single quotes.
    Lightweight splitter suitable for schema files.
    """
    stmts = []
    buf = []
    in_single = False
    in_dollar = False
    i = 0
    s = statements
    while i < len(s):
        ch = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if not in_dollar and ch == "'" and not in_single:
            in_single = True
            buf.append(ch)
        elif not in_dollar and ch == "'" and in_single:
            in_single = False
            buf.append(ch)
        elif not in_single and not in_dollar and ch == "$" and nxt == "$":
            in_dollar = True
            buf.append("$$")
            i += 1
        elif in_dollar and ch == "$" and nxt == "$":
            in_dollar = False
            buf.append("$$")
            i += 1
        elif not in_single and not in_dollar and ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts

def should_skip(stmt_lower: str) -> bool:
    # Skip invalid dump artifacts for uuid_* functions declared as LANGUAGE C (no source),
    # and their ALTER FUNCTION owner lines.
    if stmt_lower.startswith("create or replace function uuid_") and " language c" in stmt_lower:
        return True
    if stmt_lower.startswith("alter function uuid_"):
        return True
    return False

def connect_from_env():
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    sslmode = os.getenv("DB_SSLMODE")  # optional

    missing = [k for k, v in {
        "DB_NAME": name, "DB_USER": user, "DB_PASSWORD": password
    }.items() if not v]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(2)

    dsn = f"host={host} port={port} dbname={name} user={user} password={password}"
    if sslmode:
        dsn += f" sslmode={sslmode}"
    return psycopg2.connect(dsn)

def main():
    parser = argparse.ArgumentParser(description="Initialize PostgreSQL schema.")
    parser.add_argument("--sql", default="DB_schema_sql_scritp.sql",
                        help="Path to the SQL schema file.")
    parser.add_argument("--yes", action="store_true",
                        help="Run without interactive confirmation.")
    args = parser.parse_args()

    if not os.path.exists(args.sql):
        print(f"Schema file not found: {args.sql}", file=sys.stderr)
        sys.exit(1)

    if not args.yes:
        print(textwrap.dedent(f"""
            This will connect to Postgres using env vars (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
            and apply schema from:
              {os.path.abspath(args.sql)}

            It will:
             - CREATE EXTENSION uuid-ossp, pgcrypto (idempotent)
             - Execute statements one-by-one
             - Skip invalid uuid_* C-language function stubs found in dumps

            Continue? [y/N]
        """).strip())
        ans = input("> ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    conn = connect_from_env()
    conn.autocommit = True
    cur = conn.cursor()

    executed = 0
    skipped = 0
    failed = 0

    try:
        # Ensure extensions
        for ext_stmt in split_sql(EXT_SETUP):
            try:
                cur.execute(ext_stmt)
                executed += 1
            except Exception as e:
                failed += 1
                print(f"[EXT ERR] {e}")

        # Load and run schema
        with open(args.sql, "r", encoding="utf-8") as f:
            sql_text = f.read()

        for stmt in split_sql(sql_text):
            lower = stmt.strip().lower()
            if should_skip(lower):
                skipped += 1
                head = stmt.splitlines()[0] if stmt.splitlines() else stmt[:120]
                print(f"[SKIP] {head[:120]}...")
                continue
            try:
                cur.execute(stmt)
                executed += 1
            except Exception as e:
                failed += 1
                head = stmt.splitlines()[0] if stmt.splitlines() else stmt[:200]
                print(f"[ERR] {e}\n  at: {head[:200]}...")

        print(f"\nDone. Executed: {executed}, Skipped: {skipped}, Failed: {failed}")
        if failed:
            print("Some statements failed. Review errors above; many are safe (exists/ownership).")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
