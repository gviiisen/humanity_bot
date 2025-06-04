import sqlite3
import threading
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pytz

# 设置上海时区
SHANGHAI_TZ = pytz.timezone('Asia/Shanghai')

class AccountDatabase:
    def __init__(self, db_path: str = "accounts.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path)
            # 启用外键约束
            self._local.conn.execute("PRAGMA foreign_keys = ON")
            # 设置行工厂为字典
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    address TEXT PRIMARY KEY,
                    private_key TEXT NOT NULL,
                    token TEXT,
                    hp_token TEXT,
                    last_claim_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_claim ON accounts(last_claim_time)")

    def add_account(self, address: str, private_key: str) -> bool:
        """添加新账号"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO accounts (address, private_key) VALUES (?, ?)",
                    (address, private_key)
                )
                return True
        except sqlite3.IntegrityError:
            return False

    def update_tokens(self, address: str, token: Optional[str] = None, hp_token: Optional[str] = None):
        """更新账号的token信息"""
        with self._get_conn() as conn:
            updates = []
            params = []
            if token is not None:
                updates.append("token = ?")
                params.append(token)
            if hp_token is not None:
                updates.append("hp_token = ?")
                params.append(hp_token)
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                query = f"UPDATE accounts SET {', '.join(updates)} WHERE address = ?"
                params.append(address)
                conn.execute(query, params)

    def update_claim_time(self, address: str):
        """更新领取时间为当前上海时间"""
        with self._get_conn() as conn:
            # 获取当前上海时间
            now = datetime.now(SHANGHAI_TZ)
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            
            conn.execute(
                """
                UPDATE accounts 
                SET last_claim_time = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE address = ?
                """,
                (now_str, address)
            )

    def get_account(self, address: str) -> Optional[Dict[str, Any]]:
        """获取账号信息"""
        with self._get_conn() as conn:
            result = conn.execute(
                "SELECT * FROM accounts WHERE address = ?",
                (address,)
            ).fetchone()
            return dict(result) if result else None

    def get_claimable_accounts(self, batch_size: int = 100) -> list:
        """获取可以领取奖励的账号"""
        with self._get_conn() as conn:
            # 获取当前上海时间24小时前的时间戳
            now = datetime.now(SHANGHAI_TZ)
            one_day_ago = now - timedelta(days=1)
            one_day_ago_str = one_day_ago.strftime('%Y-%m-%d %H:%M:%S')
            
            results = conn.execute(
                """
                SELECT * FROM accounts 
                WHERE last_claim_time IS NULL 
                OR last_claim_time <= ?
                LIMIT ?
                """,
                (one_day_ago_str, batch_size)
            ).fetchall()
            return [dict(row) for row in results]

    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, "conn"):
            self._local.conn.close()
            del self._local.conn 