"""FR-1 成員設定的 HTTP 介面：新增（NFR-1 請求 ID）、列出、查詢、修改（含停用）、刪除，以及可選的轉接器清單。

轉接器、認證模式、推理強度是否合法一律查轉接器登記處（NFR-7），不在這裡列出固定幾家。
模型：轉接器能提供模型清單之前先存文字，不比對清單（SPEC FR-1 分期）。
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import time
import unicodedata
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services import adapters
from app.services.turn_contract import request_id as checked_uuid
from app.storage import db, members, requests


KIND = 'member_create'
DEFAULT_KIND = 'member_default'  # 系統建立的預設成員（FR-1）
DEFAULT_AUTH_MODE = 'api_key'  # 預設成員一律用 API key 模式（基準，每家都支援）
TIMEOUT_MINUTES_DEFAULT = 15  # FR-1：預設 15 分鐘，範圍 1～60 分鐘
BUDGET_FIELD = 'max_budget_usd'
BUDGET_DEFAULT_USD = 1.0  # FR-1：支援花費上限的成員預設 1 美元（擁有者 2026-11-15 選定）
BUDGET_MIN_USD, BUDGET_MAX_USD = 0.01, 100.0
BUDGET_SCHEMA_VERSION = 8  # 資料庫第 8 版加上花費上限欄位；從更舊的版本升級時補預設值
SUBSCRIPTION_CLI = 'subscription_cli'
TERMS_NOTICE = '使用時須遵守該家的服務條款，由擁有者自行負責。'  # FR-1：選訂閱 CLI 模式時的提示

MODEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}')
EFFORT = re.compile(r'[a-z][a-z0-9_-]{0,19}')

router = APIRouter()


def seed_default_members(connection, *, clock=time.time) -> None:
    """FR-1 預設成員：依登記處順序，每個轉接器建一位（名稱是轉接器名稱、模型空白、不指定推理強度、
    API key 模式、預設逾時、啟用）。必須在資料庫第一次建立的交易裡執行，見 prepare_database。"""
    now = clock()
    for entry in adapters.adapters():
        if DEFAULT_AUTH_MODE not in entry.auth_modes:
            raise ValueError('轉接器 %s 不支援 API key 模式，無法建立預設成員' % entry.code)
        member_id = str(uuid.uuid4())
        requests.record(connection, member_id, DEFAULT_KIND, {'adapter': entry.code}, now)
        members.insert(connection, member_id, adapter=entry.code, name=entry.name, model='', effort=None,
                       auth_mode=DEFAULT_AUTH_MODE, timeout=TIMEOUT_MINUTES_DEFAULT * 60, now=now,
                       max_budget_usd=default_budget(entry, DEFAULT_AUTH_MODE))


def supports_budget(entry: adapters.Adapter, auth_mode: str) -> bool:
    """這個轉接器在這種認證模式下能不能設定花費上限（FR-1），依登記處的回合欄位判斷。"""
    return auth_mode in entry.auth_modes and BUDGET_FIELD in entry.fields_for(auth_mode)


def default_budget(entry: adapters.Adapter, auth_mode: str) -> float | None:
    return BUDGET_DEFAULT_USD if supports_budget(entry, auth_mode) else None


def fill_default_budgets(connection, previous: int) -> None:
    """FR-1：從還沒有花費上限欄位的版本升級時，支援上限的既有成員補上預設值，其他維持空白。
    在升級的同一個交易裡執行（db.migrate 的 on_upgrade）。"""
    if previous >= BUDGET_SCHEMA_VERSION:
        return
    for row in members.all_members(connection):
        if adapters.is_registered(row['adapter']) and default_budget(adapters.get(row['adapter']), row['auth_mode']):
            connection.execute('UPDATE members SET max_budget_usd = ? WHERE id = ?', (BUDGET_DEFAULT_USD, row['id']))


def prepare_database(state_dir) -> Path:
    """建立或升級狀態資料庫；第一次建立時一併建立預設成員，從舊版本升級時補上需要的預設值。
    伺服器與指令列都經過這裡，不論哪一個先建立資料庫，預設成員都只建一次。"""
    return db.prepare(state_dir, on_create=seed_default_members, on_upgrade=fill_default_budgets)


def _name(value: str) -> str:
    value = value.strip()
    if not 0 < len(value) <= 80 or any(unicodedata.category(ch).startswith('C') for ch in value):
        raise ValueError('名稱必須是 1～80 個可顯示的字')
    return value


def _model(value: str) -> str:
    if value and not MODEL.fullmatch(value):
        raise ValueError('模型名稱格式不對')
    return value


def _effort(value: str | None) -> str | None:
    if value is not None and not EFFORT.fullmatch(value):
        raise ValueError('推理強度格式不對')
    return value


def _budget(value):
    """花費上限：None（不設上限），或 0.01～100 美元、最多兩位小數的數字。"""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('花費上限必須是數字')
    if not BUDGET_MIN_USD <= value <= BUDGET_MAX_USD or abs(value * 100 - round(value * 100)) > 1e-6:
        raise ValueError('花費上限必須是 0.01～100 美元，最多兩位小數')
    return round(float(value), 2)


class MemberCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    request_id: str
    adapter: str
    name: str
    model: str = ''
    effort: str | None = None
    auth_mode: str
    timeout_minutes: int = Field(TIMEOUT_MINUTES_DEFAULT, ge=1, le=60, strict=True)
    # 沒送這個欄位時，支援花費上限的成員用預設值（FR-1）；送 null 表示不設上限。
    max_budget_usd: float | None = None

    @field_validator('max_budget_usd', mode='before')
    @classmethod
    def check_budget(cls, value):
        return _budget(value)

    @field_validator('request_id')
    @classmethod
    def check_request_id(cls, value: str) -> str:
        return checked_uuid(value)

    @field_validator('name')
    @classmethod
    def check_name(cls, value: str) -> str:
        return _name(value)

    @field_validator('model')
    @classmethod
    def check_model(cls, value: str) -> str:
        return _model(value)

    @field_validator('effort')
    @classmethod
    def check_effort(cls, value: str | None) -> str | None:
        return _effort(value)


class MemberUpdate(BaseModel):
    """只送要改的欄位。轉接器不能改（送了會被拒絕）；effort、max_budget_usd 送 null 表示清除。"""
    model_config = ConfigDict(extra='forbid')

    name: str | None = None
    model: str | None = None
    effort: str | None = None
    auth_mode: str | None = None
    timeout_minutes: int | None = Field(None, ge=1, le=60, strict=True)
    enabled: bool | None = Field(None, strict=True)
    max_budget_usd: float | None = None

    @field_validator('max_budget_usd', mode='before')
    @classmethod
    def check_budget(cls, value):
        return _budget(value)

    @field_validator('name')
    @classmethod
    def check_name(cls, value: str | None) -> str | None:
        return value if value is None else _name(value)

    @field_validator('model')
    @classmethod
    def check_model(cls, value: str | None) -> str | None:
        return value if value is None else _model(value)

    @field_validator('effort')
    @classmethod
    def check_effort(cls, value: str | None) -> str | None:
        return _effort(value)


def settable_fields(entry: adapters.Adapter) -> frozenset:
    """成員可以設定的回合欄位；新增、修改成員的檢查與轉接器清單共用，兩邊才不會不一致。"""
    return entry.turn_fields.union(*entry.mode_fields.values())


def check_against_registry(adapter: str, auth_mode: str, model: str, effort: str | None,
                           budget: float | None = None) -> None:
    """依登記處檢查；不合法丟 HTTPException(422)，錯誤訊息不帶入原值。"""
    if not adapters.is_registered(adapter):
        raise HTTPException(status_code=422, detail='未登記的轉接器')
    entry = adapters.get(adapter)
    fields = settable_fields(entry)
    if auth_mode not in entry.auth_modes:
        raise HTTPException(status_code=422, detail='這個轉接器不支援這種認證模式')
    if model and 'model' not in fields:
        raise HTTPException(status_code=422, detail='這個轉接器不支援指定模型')
    if effort is not None and 'effort' not in fields:
        raise HTTPException(status_code=422, detail='這個轉接器不支援推理強度')
    if budget is not None and not supports_budget(entry, auth_mode):
        raise HTTPException(status_code=422, detail='這個轉接器在這種認證模式下不支援花費上限')


def view(row, status: str) -> dict:
    entry = adapters.get(row['adapter']) if adapters.is_registered(row['adapter']) else None
    return {
        'id': row['id'],
        'adapter': row['adapter'],
        'adapter_name': entry.name if entry is not None else None,  # 轉接器已從登記處移除時為 None
        'name': row['name'],
        'model': row['model'],
        'effort': row['effort'],
        'auth_mode': row['auth_mode'],
        'timeout_minutes': row['timeout'] // 60,
        'max_budget_usd': row['max_budget_usd'],
        'enabled': bool(row['enabled']),
        'status': status,
        'terms_notice': TERMS_NOTICE if row['auth_mode'] == SUBSCRIPTION_CLI else None,
        'created': row['created'],
        'updated': row['updated'],
    }


def _db_path(request: Request):
    return request.app.state.db_path


@router.get('/api/adapters')
def list_adapters(request: Request):
    """成員設定可選的轉接器與支援項目，依登記順序（NFR-7）。

    available 只代表伺服器目前有這家的執行者（沒有時送出回合回 503），不代表 CLI 已安裝或已登入。
    不回傳給調度用的能力描述、模型等級、socket 位置與認證模式專屬欄位。"""
    service = request.app.state.turns
    listed = []
    for entry in adapters.adapters():
        fields = settable_fields(entry)
        listed.append({'code': entry.code, 'name': entry.name, 'auth_modes': list(entry.auth_modes),
                       'supports_model': 'model' in fields, 'supports_effort': 'effort' in fields,
                       'budget_modes': [mode for mode in entry.auth_modes if supports_budget(entry, mode)],
                       'available': service.runner_for(entry.code) is not None})
    return {'adapters': listed, 'terms_notice': TERMS_NOTICE}


def _member_id(member_id: str) -> str:
    try:
        return checked_uuid(member_id)
    except ValueError:
        raise HTTPException(status_code=422, detail='成員識別無效') from None


def _one(connection, member_id: str) -> dict | None:
    row = members.get(connection, member_id)
    return None if row is None else view(row, members.status(connection, member_id))


@router.post('/api/members')
def create_member(body: MemberCreate, path: Annotated[object, Depends(_db_path)]):
    check_against_registry(body.adapter, body.auth_mode, body.model, body.effort, body.max_budget_usd)
    budget = (body.max_budget_usd if 'max_budget_usd' in body.model_fields_set
              else default_budget(adapters.get(body.adapter), body.auth_mode))
    payload = body.model_dump(exclude={'request_id'})
    connection = db.connect(path)
    try:
        claim = requests.claim(
            connection, body.request_id, KIND, payload, clock=time.time,
            on_claim=lambda c, now: members.insert(
                c, body.request_id, adapter=body.adapter, name=body.name, model=body.model, effort=body.effort,
                auth_mode=body.auth_mode, timeout=body.timeout_minutes * 60, now=now, max_budget_usd=budget))
        member = _one(connection, body.request_id)
    finally:
        connection.close()
    if claim.outcome == requests.REJECTED:
        return JSONResponse({'detail': '這個請求 ID 已用於不同內容'}, status_code=409)
    if member is None:
        if claim.state == 'deleted':
            return JSONResponse({'detail': '這位成員已被刪除'}, status_code=410)
        return JSONResponse({'detail': '這個請求 ID 已用於其他用途'}, status_code=409)
    return JSONResponse({'member': member}, status_code=201 if claim.outcome == requests.CLAIMED else 200)


@router.get('/api/members')
def list_members(path: Annotated[object, Depends(_db_path)]):
    connection = db.connect(path)
    try:
        return {'members': [view(row, members.status(connection, row['id']))
                            for row in members.all_members(connection)]}
    finally:
        connection.close()


@router.get('/api/members/{member_id}')
def get_member(member_id: Annotated[str, Depends(_member_id)], path: Annotated[object, Depends(_db_path)]):
    connection = db.connect(path)
    try:
        member = _one(connection, member_id)
    finally:
        connection.close()
    if member is None:
        raise HTTPException(status_code=404, detail='找不到這位成員')
    return {'member': member}


@router.patch('/api/members/{member_id}')
def update_member(member_id: Annotated[str, Depends(_member_id)], body: MemberUpdate,
                  path: Annotated[object, Depends(_db_path)]):
    given = body.model_dump(include=body.model_fields_set)
    if any(value is None for key, value in given.items() if key not in ('effort', 'max_budget_usd')):
        raise HTTPException(status_code=422, detail='只有推理強度與花費上限可以清除')
    connection = db.connect(path)
    try:
        row = members.get(connection, member_id)
        if row is None:
            raise HTTPException(status_code=404, detail='找不到這位成員')
        checked = ('auth_mode', 'model', 'effort', 'max_budget_usd')
        merged = {key: row[key] for key in checked} | {key: given[key] for key in checked if key in given}
        check_against_registry(row['adapter'], merged['auth_mode'], merged['model'], merged['effort'],
                               merged['max_budget_usd'])
        changes = {('timeout' if key == 'timeout_minutes' else key): (value * 60 if key == 'timeout_minutes' else value)
                   for key, value in given.items()}
        members.update(connection, member_id, changes, time.time())
        member = _one(connection, member_id)
    finally:
        connection.close()
    return {'member': member}


@router.delete('/api/members/{member_id}', status_code=204)
def delete_member(member_id: Annotated[str, Depends(_member_id)], path: Annotated[object, Depends(_db_path)]):
    connection = db.connect(path)
    try:
        deleted = members.delete(connection, member_id, time.time())
    except members.MemberBusy:
        raise HTTPException(status_code=409, detail='這位成員還有進行中的回合，不能刪除') from None
    finally:
        connection.close()
    if not deleted:
        raise HTTPException(status_code=404, detail='找不到這位成員')
