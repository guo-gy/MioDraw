import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  nickname TEXT NOT NULL,
  avatar_url TEXT NOT NULL,
  bio TEXT NOT NULL,
  credits INTEGER NOT NULL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_subject TEXT NOT NULL,
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  user_id TEXT PRIMARY KEY,
  default_visibility TEXT NOT NULL,
  notifications INTEGER NOT NULL,
  language TEXT NOT NULL,
  theme TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS credit_transactions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  type TEXT NOT NULL,
  amount INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  title TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS payment_orders (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  package_id TEXT NOT NULL,
  credits INTEGER NOT NULL,
  price REAL NOT NULL,
  currency TEXT NOT NULL,
  status TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_order_id TEXT NOT NULL,
  payment_url TEXT NOT NULL,
  created_at REAL NOT NULL,
  paid_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS payment_events (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS artworks (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  prompt TEXT NOT NULL,
  negative_prompt TEXT NOT NULL,
  image_url TEXT NOT NULL,
  category TEXT NOT NULL,
  visibility TEXT NOT NULL,
  style TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  liked INTEGER NOT NULL DEFAULT 0,
  favorited INTEGER NOT NULL DEFAULT 0,
  likes INTEGER NOT NULL DEFAULT 0,
  collects INTEGER NOT NULL DEFAULT 0,
  params TEXT NOT NULL,
  is_gallery INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS prompts (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  category TEXT NOT NULL,
  visibility TEXT NOT NULL,
  uses INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  cover_image_url TEXT NOT NULL,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  image_url TEXT NOT NULL,
  task_id TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS generation_tasks (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  prompt TEXT NOT NULL,
  status TEXT NOT NULL,
  image_url TEXT NOT NULL,
  artwork_id TEXT NOT NULL,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  error TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS editor_tasks (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  image_id TEXT NOT NULL,
  source_image_url TEXT NOT NULL,
  mask_data TEXT NOT NULL,
  prompt TEXT NOT NULL,
  status TEXT NOT NULL,
  result_image_url TEXT NOT NULL,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS follows (
  user_id TEXT NOT NULL,
  target_user_id TEXT NOT NULL,
  followed_at REAL NOT NULL,
  PRIMARY KEY (user_id, target_user_id)
);
CREATE TABLE IF NOT EXISTS storage_objects (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  source_url TEXT NOT NULL,
  public_url TEXT NOT NULL,
  provider TEXT NOT NULL,
  purpose TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_identities (
  user_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_subject TEXT NOT NULL,
  raw TEXT NOT NULL,
  created_at REAL NOT NULL,
  PRIMARY KEY (provider, provider_subject)
);
CREATE TABLE IF NOT EXISTS sms_codes (
  phone TEXT PRIMARY KEY,
  code TEXT NOT NULL,
  expires_at REAL NOT NULL,
  consumed INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS blocks (
  user_id TEXT NOT NULL,
  target_user_id TEXT NOT NULL,
  blocked_at REAL NOT NULL,
  PRIMARY KEY (user_id, target_user_id)
);
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS moderation_events (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  status TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at REAL NOT NULL
);
"""


MYSQL_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id VARCHAR(64) PRIMARY KEY,
  nickname VARCHAR(255) NOT NULL,
  avatar_url TEXT NOT NULL,
  bio TEXT NOT NULL,
  credits INT NOT NULL,
  created_at DOUBLE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS sessions (
  token VARCHAR(96) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  provider VARCHAR(32) NOT NULL,
  provider_subject VARCHAR(191) NOT NULL,
  created_at DOUBLE NOT NULL,
  expires_at DOUBLE NOT NULL,
  INDEX idx_sessions_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS settings (
  user_id VARCHAR(64) PRIMARY KEY,
  default_visibility VARCHAR(32) NOT NULL,
  notifications TINYINT NOT NULL,
  language VARCHAR(32) NOT NULL,
  theme VARCHAR(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS credit_transactions (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  type VARCHAR(32) NOT NULL,
  amount INT NOT NULL,
  balance_after INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  created_at DOUBLE NOT NULL,
  INDEX idx_credit_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS payment_orders (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  package_id VARCHAR(64) NOT NULL,
  credits INT NOT NULL,
  price DOUBLE NOT NULL,
  currency VARCHAR(16) NOT NULL,
  status VARCHAR(32) NOT NULL,
  provider VARCHAR(32) NOT NULL,
  provider_order_id VARCHAR(128) NOT NULL,
  payment_url TEXT NOT NULL,
  created_at DOUBLE NOT NULL,
  paid_at DOUBLE NOT NULL,
  INDEX idx_payment_user_time (user_id, created_at),
  INDEX idx_payment_provider_order (provider_order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS payment_events (
  id VARCHAR(64) PRIMARY KEY,
  order_id VARCHAR(64) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  payload LONGTEXT NOT NULL,
  created_at DOUBLE NOT NULL,
  INDEX idx_payment_events_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS artworks (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  title VARCHAR(255) NOT NULL,
  prompt LONGTEXT NOT NULL,
  negative_prompt LONGTEXT NOT NULL,
  image_url TEXT NOT NULL,
  category VARCHAR(64) NOT NULL,
  visibility VARCHAR(32) NOT NULL,
  style VARCHAR(128) NOT NULL,
  width INT NOT NULL,
  height INT NOT NULL,
  liked TINYINT NOT NULL DEFAULT 0,
  favorited TINYINT NOT NULL DEFAULT 0,
  likes INT NOT NULL DEFAULT 0,
  collects INT NOT NULL DEFAULT 0,
  params LONGTEXT NOT NULL,
  is_gallery TINYINT NOT NULL DEFAULT 0,
  created_at DOUBLE NOT NULL,
  INDEX idx_artworks_user_time (user_id, created_at),
  INDEX idx_artworks_gallery (visibility, is_gallery, collects),
  INDEX idx_artworks_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS prompts (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  title VARCHAR(255) NOT NULL,
  content LONGTEXT NOT NULL,
  category VARCHAR(64) NOT NULL,
  visibility VARCHAR(32) NOT NULL,
  uses INT NOT NULL DEFAULT 0,
  created_at DOUBLE NOT NULL,
  INDEX idx_prompts_user_time (user_id, created_at),
  INDEX idx_prompts_public (visibility, uses)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS conversations (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  title VARCHAR(255) NOT NULL,
  cover_image_url TEXT NOT NULL,
  created_at DOUBLE NOT NULL,
  updated_at DOUBLE NOT NULL,
  INDEX idx_conversations_user_time (user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS messages (
  id VARCHAR(64) PRIMARY KEY,
  conversation_id VARCHAR(64) NOT NULL,
  role VARCHAR(32) NOT NULL,
  content LONGTEXT NOT NULL,
  image_url TEXT NOT NULL,
  task_id VARCHAR(64) NOT NULL,
  created_at DOUBLE NOT NULL,
  INDEX idx_messages_conversation_time (conversation_id, created_at),
  INDEX idx_messages_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS generation_tasks (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  conversation_id VARCHAR(64) NOT NULL,
  prompt LONGTEXT NOT NULL,
  status VARCHAR(32) NOT NULL,
  image_url TEXT NOT NULL,
  artwork_id VARCHAR(64) NOT NULL,
  created_at DOUBLE NOT NULL,
  updated_at DOUBLE NOT NULL,
  error TEXT NOT NULL,
  INDEX idx_generation_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS editor_tasks (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  image_id VARCHAR(64) NOT NULL,
  source_image_url TEXT NOT NULL,
  mask_data LONGTEXT NOT NULL,
  prompt LONGTEXT NOT NULL,
  status VARCHAR(32) NOT NULL,
  result_image_url TEXT NOT NULL,
  created_at DOUBLE NOT NULL,
  updated_at DOUBLE NOT NULL,
  INDEX idx_editor_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS follows (
  user_id VARCHAR(64) NOT NULL,
  target_user_id VARCHAR(64) NOT NULL,
  followed_at DOUBLE NOT NULL,
  PRIMARY KEY (user_id, target_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS storage_objects (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  source_url TEXT NOT NULL,
  public_url TEXT NOT NULL,
  provider VARCHAR(32) NOT NULL,
  purpose VARCHAR(64) NOT NULL,
  created_at DOUBLE NOT NULL,
  INDEX idx_storage_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS auth_identities (
  user_id VARCHAR(64) NOT NULL,
  provider VARCHAR(32) NOT NULL,
  provider_subject VARCHAR(191) NOT NULL,
  raw LONGTEXT NOT NULL,
  created_at DOUBLE NOT NULL,
  PRIMARY KEY (provider, provider_subject),
  INDEX idx_auth_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS sms_codes (
  phone VARCHAR(32) PRIMARY KEY,
  code VARCHAR(16) NOT NULL,
  expires_at DOUBLE NOT NULL,
  consumed TINYINT NOT NULL DEFAULT 0,
  created_at DOUBLE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS blocks (
  user_id VARCHAR(64) NOT NULL,
  target_user_id VARCHAR(64) NOT NULL,
  blocked_at DOUBLE NOT NULL,
  PRIMARY KEY (user_id, target_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS reports (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  target_type VARCHAR(32) NOT NULL,
  target_id VARCHAR(64) NOT NULL,
  reason TEXT NOT NULL,
  status VARCHAR(32) NOT NULL,
  created_at DOUBLE NOT NULL,
  INDEX idx_reports_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS moderation_events (
  id VARCHAR(64) PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  target_type VARCHAR(32) NOT NULL,
  target_id VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  reason TEXT NOT NULL,
  created_at DOUBLE NOT NULL,
  INDEX idx_moderation_user_time (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def row_to_dict(row: Any) -> Dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    return dict(row)


def mysql_address() -> tuple[str, int]:
    address = os.getenv("MYSQL_ADDRESS", "").strip()
    if address:
        host, _, port = address.partition(":")
        return host, int(port or "3306")
    return os.getenv("MYSQL_HOST", "127.0.0.1"), int(os.getenv("MYSQL_PORT", "3306"))


def convert_mysql_sql(sql: str) -> str:
    converted = sql.replace("INSERT OR IGNORE INTO", "INSERT IGNORE INTO")
    converted = converted.replace("INSERT OR REPLACE INTO", "REPLACE INTO")
    converted = converted.replace("MAX(collects, likes)", "GREATEST(collects, likes)")
    converted = converted.replace("MAX(0, collects + ?)", "GREATEST(0, collects + ?)")
    converted = converted.replace("MAX(0, likes + ?)", "GREATEST(0, likes + ?)")
    return converted.replace("?", "%s")


class MySQLConnection:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def __enter__(self) -> "MySQLConnection":
        return self

    def __exit__(self, exc_type: Any, _exc: Any, _tb: Any) -> None:
        if exc_type:
            self.connection.rollback()
        else:
            self.connection.commit()
        self.connection.close()

    def execute(self, sql: str, params: tuple = ()) -> Any:
        cursor = self.connection.cursor()
        cursor.execute(convert_mysql_sql(sql), params)
        return cursor

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            sql = statement.strip()
            if sql:
                self.execute(sql)

    def commit(self) -> None:
        self.connection.commit()


class DatabaseProvider:
    name = "base"

    def connect(self) -> Any:
        raise NotImplementedError

    def init_schema(self) -> None:
        raise NotImplementedError

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self.connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return row_to_dict(row) if row else None

    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [row_to_dict(row) for row in rows]

    def health_info(self) -> str:
        return self.name


class SQLiteDatabaseProvider(DatabaseProvider):
    name = "sqlite"

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SQLITE_SCHEMA)
            conn.commit()

    def health_info(self) -> str:
        return str(self.db_path)


class MySQLDatabaseProvider(DatabaseProvider):
    name = "mysql"

    def __init__(self) -> None:
        self.host, self.port = mysql_address()
        self.user = os.getenv("MYSQL_USERNAME") or os.getenv("MYSQL_USER") or "root"
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DATABASE", "miodraw")
        self.charset = os.getenv("MYSQL_CHARSET", "utf8mb4")
        if not self.database.replace("_", "").isalnum():
            raise RuntimeError("MYSQL_DATABASE 只能包含字母、数字和下划线")

    def _pymysql(self) -> Any:
        try:
            import pymysql
            from pymysql.cursors import DictCursor
        except ImportError as error:
            raise RuntimeError("MySQL 模式需要安装 PyMySQL：pip install PyMySQL") from error
        return pymysql, DictCursor

    def _raw_connect(self, *, database: bool = True) -> Any:
        pymysql, dict_cursor = self._pymysql()
        kwargs: Dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "charset": self.charset,
            "cursorclass": dict_cursor,
            "autocommit": False,
            "connect_timeout": int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10")),
            "read_timeout": int(os.getenv("MYSQL_READ_TIMEOUT", "20")),
            "write_timeout": int(os.getenv("MYSQL_WRITE_TIMEOUT", "20")),
        }
        if database:
            kwargs["database"] = self.database
        return pymysql.connect(**kwargs)

    def connect(self) -> MySQLConnection:
        return MySQLConnection(self._raw_connect(database=True))

    def init_schema(self) -> None:
        conn = self._raw_connect(database=False)
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.database}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            conn.commit()
        finally:
            conn.close()
        with self.connect() as conn:
            conn.executescript(MYSQL_SCHEMA)
            conn.commit()

    def health_info(self) -> str:
        return f"{self.host}:{self.port}/{self.database}"


def database_provider_from_env(_data_dir: Path, db_path: Path) -> DatabaseProvider:
    provider = (os.getenv("DATABASE_PROVIDER") or os.getenv("DB_PROVIDER") or "sqlite").strip().lower()
    if provider in ("", "sqlite", "local"):
        return SQLiteDatabaseProvider(db_path)
    if provider in ("mysql", "tencent_mysql", "cloud_mysql"):
        return MySQLDatabaseProvider()
    raise RuntimeError(f"未知数据库类型：{provider}")
