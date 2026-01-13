"""Check production transactions via SSH."""
import asyncio
import os
import asyncpg
from sshtunnel import SSHTunnelForwarder


async def check_prod():
    """Check production database on VPS."""
    vps_host = os.getenv("VPS_IP", "217.171.146.4")
    vps_user = os.getenv("VPS_USER", "root")
    vps_password = os.getenv("VPS_PASSWORD")

    prod_db = os.getenv("PROD_POSTGRES_DB", "telegram_billing2")
    prod_user = os.getenv("PROD_POSTGRES_USER", "postgres")
    prod_password = os.getenv("PROD_POSTGRES_PASSWORD", "postgres")

    print(f"[*] Connecting to {vps_host} via SSH...")
    print(f"[*] Database: {prod_db}")

    # Create SSH tunnel
    tunnel = SSHTunnelForwarder(
        (vps_host, 22),
        ssh_username=vps_user,
        ssh_password=vps_password,
        remote_bind_address=('localhost', 5432),
        local_bind_address=('localhost', 15432),
    )

    try:
        tunnel.start()
        print(f"[+] SSH tunnel established on port {tunnel.local_bind_port}")

        # Connect to PostgreSQL through tunnel
        conn = await asyncpg.connect(
            host='localhost',
            port=tunnel.local_bind_port,
            user=prod_user,
            password=prod_password,
            database=prod_db,
        )

        try:
            # Check users
            print("\n[*] Checking users...")
            users = await conn.fetch("""
                SELECT id, username, first_name, token_balance, subscription_end, is_blocked
                FROM users
                ORDER BY id
            """)

            for user in users:
                print(f"\nUser {user['id']} (@{user['username']})")
                print(f"  Balance: {user['token_balance']}")
                print(f"  Sub end: {user['subscription_end']}")
                print(f"  Blocked: {user['is_blocked']}")

            # Check last transactions
            print("\n[*] Last 10 transactions:")
            txs = await conn.fetch("""
                SELECT
                    u.id as user_id,
                    t.type,
                    t.tokens_delta,
                    t.balance_after,
                    t.description,
                    t.created_at
                FROM transactions t
                JOIN users u ON t.user_id = u.id
                ORDER BY t.created_at DESC
                LIMIT 10
            """)

            if not txs:
                print("  (no transactions)")
            else:
                for tx in txs:
                    print(f"\n  User {tx['user_id']}: {tx['type']}")
                    print(f"    Delta: {tx['tokens_delta']}")
                    print(f"    Balance after: {tx['balance_after']}")
                    print(f"    Description: {tx['description']}")
                    print(f"    Time: {tx['created_at']}")

        finally:
            await conn.close()

    finally:
        tunnel.stop()
        print("\n[*] SSH tunnel closed")


if __name__ == "__main__":
    asyncio.run(check_prod())
