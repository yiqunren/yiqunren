"""後端設定：全部可由 YIQUNREN_ 開頭的環境變數覆寫（NFR-4），預設只接受本機連線（NFR-3）。"""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path


DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8420


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    state_dir: Path


def default_state_dir(env) -> Path:
    # XDG 規範：XDG_STATE_HOME 必須是絕對路徑，相對路徑一律忽略。
    base = env.get('XDG_STATE_HOME', '')
    if not base or not Path(base).is_absolute():
        home = env.get('HOME', '')
        if not home or not Path(home).is_absolute():
            raise ConfigError('找不到使用者家目錄，請設定 YIQUNREN_STATE_DIR')
        base = str(Path(home) / '.local' / 'state')
    return Path(base) / 'yiqunren'


def load(env=None) -> Settings:
    env = os.environ if env is None else env

    host = env.get('YIQUNREN_HOST', DEFAULT_HOST)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        raise ConfigError('YIQUNREN_HOST 必須是 IP 位址') from None

    raw_port = env.get('YIQUNREN_PORT', str(DEFAULT_PORT))
    if not raw_port.isascii() or not raw_port.isdigit() or not 1 <= int(raw_port) <= 65535:
        raise ConfigError('YIQUNREN_PORT 必須是 1～65535 的整數')

    raw_state = env.get('YIQUNREN_STATE_DIR', '')
    state_dir = Path(raw_state) if raw_state else default_state_dir(env)
    if not state_dir.is_absolute():
        raise ConfigError('YIQUNREN_STATE_DIR 必須是絕對路徑')

    return Settings(host=host, port=int(raw_port), state_dir=state_dir)
