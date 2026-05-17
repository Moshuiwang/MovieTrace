"""幂等创建飞书发现运行日志表字段 (P1.24-D)。

职责:
1. GET 当前字段列表
2. 创建缺失的字段 (8 个新字段 + 运营备注)
3. 重命名旧字段 "季号" → "在播最新季" (若存在)
4. 支持 dry-run 模式(只打印计划,不调用飞书)
"""

from __future__ import annotations

from movietrace.feishu._http import OPEN_API_BASE, request_json
from movietrace.feishu.baseline import fetch_tenant_access_token


# 需要创建的字段 (name, type_code)
# 飞书 field type: 1=文本, 2=数字, 5=日期, 15=URL
REQUIRED_FIELDS_FOR_DISCOVERY_TABLE: list[tuple[str, int]] = [
    ("在播最新季", 2),  # 数字
    ("单行时长(h)", 2),  # 数字
    ("IMDb 链接", 15),  # URL
    ("TMDb 链接", 15),  # URL
    ("FP 热度分", 2),  # 数字
    ("IMDb 评分", 2),  # 数字
    ("TMDb 评分", 2),  # 数字
    ("TMDb 热度分", 2),  # 数字
    ("Trakt 热度分", 2),  # 数字
    ("运营备注", 1),  # 文本
]

# 旧字段重命名映射 (old_name -> new_name)
FIELD_RENAMES: list[tuple[str, str]] = [
    ("季号", "在播最新季"),
]


def list_table_fields(token: str, app_token: str, table_id: str) -> list[dict]:
    """GET /bitable/v1/apps/{app}/tables/{table}/fields, paginate.

    返回字段列表 [{"field_id":"...", "field_name":"...", "type":int}, ...].
    """
    fields: list[dict] = []
    page_size = 100
    page_token = None

    while True:
        url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
        params = f"?page_size={page_size}"
        if page_token:
            params += f"&page_token={page_token}"

        resp = request_json("GET", url + params, token=token)

        if resp.get("code") != 0:
            code = resp.get("code")
            msg = resp.get("msg", "")
            if code in (99991661, 99991663, 1061045):
                raise RuntimeError(
                    f"Feishu field management permission denied (code={code}): {msg}. "
                    "Grant the app 'bitable:app' + 'bitable:app:fields:read' scope in the Feishu console."
                )
            raise RuntimeError(f"Feishu list fields failed (code={code}): {msg}")

        data = resp.get("data", {})
        items = data.get("items", [])
        if items:  # Only extend if items is not None/empty
            fields.extend(items)

        # Check has_more to determine if pagination should continue
        has_more = data.get("has_more", False)
        if not has_more:
            break

        page_token = data.get("page_token")
        if not page_token:
            break

    return fields


def create_table_field(token: str, app_token: str, table_id: str, field_name: str, field_type: int) -> dict:
    """POST /bitable/v1/apps/{app}/tables/{table}/fields.

    body: {"field_name": ..., "type": ...}
    """
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    payload = {
        "field_name": field_name,
        "type": field_type,
    }

    resp = request_json("POST", url, token=token, payload=payload)

    if resp.get("code") != 0:
        code = resp.get("code")
        msg = resp.get("msg", "")
        if code in (99991661, 99991663, 1061045):
            raise RuntimeError(
                f"Feishu field creation permission denied (code={code}): {msg}. "
                "Grant the app 'bitable:app' + 'bitable:app:fields:write' scope in the Feishu console."
            )
        raise RuntimeError(f"Feishu create field failed (code={code}): {msg}")

    return resp.get("data", {})


def rename_table_field(token: str, app_token: str, table_id: str, field_id: str, new_name: str, field_type: int = 2) -> dict:
    """PUT /bitable/v1/apps/{app}/tables/{table}/fields/{field_id}.

    body: {"field_name": new_name, "type": field_type}
    飞书 PUT field API 要求同时传 type，否则返回 99992402。
    """
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
    payload = {
        "field_name": new_name,
        "type": field_type,
    }

    resp = request_json("PUT", url, token=token, payload=payload)

    if resp.get("code") != 0:
        code = resp.get("code")
        msg = resp.get("msg", "")
        if code in (99991661, 99991663, 1061045):
            raise RuntimeError(
                f"Feishu field rename permission denied (code={code}): {msg}. "
                "Grant the app 'bitable:app' + 'bitable:app:fields:write' scope in the Feishu console."
            )
        raise RuntimeError(f"Feishu rename field failed (code={code}): {msg}")

    return resp.get("data", {})


def ensure_table_fields(
    *,
    app_id: str,
    app_secret: str,
    app_token: str,
    table_id: str,
    required: list[tuple[str, int]] = REQUIRED_FIELDS_FOR_DISCOVERY_TABLE,
    renames: list[tuple[str, str]] = FIELD_RENAMES,
    dry_run: bool = False,
) -> dict:
    """幂等创建缺失字段 + 重命名旧字段。

    返回 {"created": [...], "existed": [...], "renamed": [...], "errors": [...]}.

    流程:
    1. fetch_tenant_access_token(app_id, app_secret)
    2. list 当前字段 → {name: field}
    3. 应用 renames: 对每个 (old, new),如果 old 存在 → PUT 改名为 new
       (改名后视为 new 已存在)
    4. 应用 required: 对每个 (name, type),如果不存在 → POST 创建
       (existed 仅记录,不重复创建)
    5. dry_run 模式只打印计划,不实际调用

    失败处置:
    - 99991661 / 99991663 / 1061045 (权限不足):
      raise RuntimeError 携带提示
    - 其他 code != 0: raise RuntimeError 携带 code + msg
    - 不静默重试
    """
    result = {
        "created": [],
        "existed": [],
        "renamed": [],
        "errors": [],
        "dry_run": dry_run,
    }

    # 获取 token
    try:
        token = fetch_tenant_access_token(app_id, app_secret)
    except Exception as e:
        result["errors"].append(f"Token fetch failed: {e}")
        return result

    # 列举当前字段
    try:
        current_fields = list_table_fields(token, app_token, table_id)
    except Exception as e:
        result["errors"].append(f"Field list failed: {e}")
        raise  # 列举失败时直接抛错

    # 构建 name → field 映射
    field_by_name: dict[str, dict] = {f.get("field_name", ""): f for f in current_fields}

    # 应用 renames
    for old_name, new_name in renames:
        if old_name not in field_by_name:
            # 旧字段不存在,跳过
            continue

        old_field = field_by_name[old_name]
        field_id = old_field.get("field_id", "")

        if new_name in field_by_name:
            # 新字段名已存在,跳过 rename(防止同名冲突)
            result["errors"].append(
                f"Cannot rename '{old_name}' to '{new_name}': target already exists"
            )
            continue

        if dry_run:
            result["renamed"].append({"old_name": old_name, "new_name": new_name, "field_id": field_id})
        else:
            try:
                rename_table_field(token, app_token, table_id, field_id, new_name, old_field.get("type", 2))
                result["renamed"].append({"old_name": old_name, "new_name": new_name})
                # 更新 field_by_name 映射
                del field_by_name[old_name]
                field_by_name[new_name] = old_field
            except Exception as e:
                result["errors"].append(f"Rename '{old_name}' failed: {e}")
                raise

    # 应用 required
    for field_name, field_type in required:
        if field_name in field_by_name:
            # 字段已存在
            result["existed"].append({"field_name": field_name, "field_type": field_type})
        else:
            # 字段缺失,需要创建
            if dry_run:
                result["created"].append({"field_name": field_name, "field_type": field_type})
            else:
                try:
                    create_table_field(token, app_token, table_id, field_name, field_type)
                    result["created"].append({"field_name": field_name, "field_type": field_type})
                except Exception as e:
                    result["errors"].append(f"Create '{field_name}' failed: {e}")
                    raise

    return result
