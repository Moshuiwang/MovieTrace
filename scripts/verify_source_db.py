"""验证 A 库（生产环境 DB 导出的两张表）的读取与结构。

输入：source_records/节目数据.csv + source_records/子节目数据.csv
输出：终端统计 + 关键发现（纯验证，不改任何数据）
"""

import csv
import json
import os
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROGRAM_CSV = PROJECT_ROOT / "source_records" / "节目数据.csv"
EPISODE_CSV = PROJECT_ROOT / "source_records" / "子节目数据.csv"


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    """读取 CSV，返回 (字段名列表, 行列表)。处理被引号包裹的多行字段。"""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            # 清理 BOM
            if i == 0:
                cleaned = {}
                for k, v in row.items():
                    clean_k = k.lstrip("﻿").strip()
                    cleaned[clean_k] = v
                row = cleaned
            rows.append(row)
        return reader.fieldnames or [], rows


def analyse_programs(rows: list[dict]) -> dict:
    """节目表分析"""
    n = len(rows)
    report = {"total_rows": n}

    # 字段列表
    if rows:
        report["columns"] = list(rows[0].keys())
        report["n_columns"] = len(rows[0])

    # program_status 分布
    status_counts = Counter(r.get("program_status", "") for r in rows)
    report["program_status_distribution"] = dict(status_counts)

    # make_by_star 分布 (是否明星制作)
    star_counts = Counter(r.get("make_by_star", "") for r in rows)
    report["make_by_star_distribution"] = dict(star_counts)

    # delete_flag 分布
    del_counts = Counter(r.get("delete_flag", "") for r in rows)
    report["delete_flag_distribution"] = dict(del_counts)

    # online_flag 分布
    online_counts = Counter(r.get("online_flag", "") for r in rows)
    report["online_flag_distribution"] = dict(online_counts)

    # imdb_id 填充率
    imdb_filled = sum(1 for r in rows if r.get("imdb_id", "").strip())
    report["imdb_id_fill_rate"] = f"{imdb_filled}/{n} ({100*imdb_filled/n:.1f}%)"

    # make_year 填充率
    year_filled = sum(1 for r in rows if r.get("make_year", "").strip())
    report["make_year_fill_rate"] = f"{year_filled}/{n} ({100*year_filled/n:.1f}%)"

    # tenant_id 分布
    tenant_counts = Counter(r.get("tenant_id", "") for r in rows)
    report["tenant_id_distribution"] = dict(tenant_counts)

    # 样本名（前 10 条 name）
    report["sample_names"] = [r.get("name", "") for r in rows[:10]]

    # 名字中含 S\d\d 的节目数（命名的季号）
    s_pattern_count = sum(1 for r in rows if "S" in r.get("name", "") and any(c.isdigit() for c in r.get("name", "").split("S")[-1][:2] if c.isdigit()))
    report["names_with_sNN_pattern_estimate"] = s_pattern_count

    # 名字中含 E\d\d 的节目数
    e_pattern_count = sum(1 for r in rows if "E" in r.get("name", "") and any(c.isdigit() for c in r.get("name", "").split("E")[-1][:2] if c.isdigit()))
    report["names_with_eNN_pattern_estimate"] = e_pattern_count

    return report


def analyse_episodes(rows: list[dict]) -> dict:
    """子节目表分析"""
    n = len(rows)
    report = {"total_rows": n}

    if rows:
        report["columns"] = list(rows[0].keys())
        report["n_columns"] = len(rows[0])

    # video_status 分布
    vs_counts = Counter(r.get("video_status", "") for r in rows)
    report["video_status_distribution"] = dict(vs_counts)

    # delete_flag
    del_counts = Counter(r.get("delete_flag", "") for r in rows)
    report["delete_flag_distribution"] = dict(del_counts)

    # online_flag
    online_counts = Counter(r.get("online_flag", "") for r in rows)
    report["online_flag_distribution"] = dict(online_counts)

    # source_type 分布
    st_counts = Counter(r.get("source_type", "") for r in rows)
    report["source_type_distribution"] = dict(st_counts)

    # dot_status (打点状态)
    dot_counts = Counter(r.get("dot_status", "") for r in rows)
    report["dot_status_distribution"] = dict(dot_counts)

    # 关联字段: fk_program_content_id 填充率
    fk_filled = sum(1 for r in rows if r.get("fk_program_content_id", "").strip())
    report["fk_program_content_id_fill_rate"] = f"{fk_filled}/{n} ({100*fk_filled/n:.1f}%)"

    # pc_type 分布 (父节目的类型)
    pctype_counts = Counter(r.get("pc_type", "") for r in rows)
    report["pc_type_distribution"] = dict(pctype_counts)

    # pc_program_status 分布
    pcstatus_counts = Counter(r.get("pc_program_status", "") for r in rows)
    report["pc_program_status_distribution"] = dict(pcstatus_counts)

    # pc_imdb_id 填充率
    pc_imdb_filled = sum(1 for r in rows if r.get("pc_imdb_id", "").strip())
    report["pc_imdb_id_fill_rate"] = f"{pc_imdb_filled}/{n} ({100*pc_imdb_filled/n:.1f}%)"

    # 子节目 ID 总数 vs 去重
    unique_ids = {r.get("id", "") for r in rows if r.get("id")}
    report["unique_id_count"] = len(unique_ids)

    # 每个节目的子节目数量分布 (top 20)
    parent_counts = Counter(r.get("fk_program_content_id", "") for r in rows)
    report["children_per_parent_top20"] = parent_counts.most_common(20)
    report["total_unique_parents"] = len(parent_counts)
    report["avg_children_per_parent"] = round(n / len(parent_counts), 1) if parent_counts else 0

    # 样本名
    report["sample_names"] = [r.get("name", "") for r in rows[:10]]

    return report


def cross_analysis(program_rows: list[dict], episode_rows: list[dict]) -> dict:
    """关联分析"""
    report = {}

    # 建立节目 ID → 行 的索引
    program_by_id = {r["id"]: r for r in program_rows if r.get("id")}

    # 子节目中引用的父节目 ID
    parent_ids_in_episodes = {r.get("fk_program_content_id", "") for r in episode_rows}
    parent_ids_in_episodes.discard("")

    # 有多少子节目的父 ID 在节目表中能找到
    matched = parent_ids_in_episodes & set(program_by_id.keys())
    orphan = parent_ids_in_episodes - set(program_by_id.keys())

    report["total_program_ids"] = len(program_by_id)
    report["unique_fk_program_content_ids_in_episodes"] = len(parent_ids_in_episodes)
    report["matched_parent_ids"] = len(matched)
    report["orphan_parent_ids_in_episodes"] = len(orphan)
    report["orphan_examples"] = list(orphan)[:5] if orphan else []

    # 节目表中没有被任何子节目引用的节目（孤独节目）
    referenced_parents = {r.get("fk_program_content_id", "") for r in episode_rows}
    unreferenced = set(program_by_id.keys()) - referenced_parents
    report["unreferenced_programs"] = len(unreferenced)
    report["unreferenced_examples"] = [
        program_by_id[pid].get("name", "") for pid in list(unreferenced)[:10]
    ]

    # 通过子节目的 pc_* 字段看父节目信息是否与节目表一致
    # pc_name 与 节目.name 对比
    mismatch_count = 0
    mismatch_examples = []
    for ep in episode_rows:
        pc_id = ep.get("pc_id", "").strip()
        pc_name = ep.get("pc_name", "").strip()
        if pc_id and pc_id in program_by_id:
            prog_name = program_by_id[pc_id].get("name", "")
            if pc_name != prog_name:
                mismatch_count += 1
                if len(mismatch_examples) < 5:
                    mismatch_examples.append({
                        "pc_id": pc_id,
                        "pc_name": pc_name,
                        "program_name": prog_name,
                    })
    report["pc_name_vs_program_name_mismatches"] = mismatch_count
    report["mismatch_examples"] = mismatch_examples

    return report


def extract_program_name_structure(rows: list[dict]) -> dict:
    """从节目 name 中提取季号/集号模式"""
    import re

    report = {}
    s_pattern = re.compile(r"S(\d{1,3})", re.IGNORECASE)
    e_pattern = re.compile(r"E(\d{1,3})", re.IGNORECASE)

    season_numbers = Counter()
    has_s = 0
    has_e = 0
    no_s = 0
    examples_no_s = []

    for r in rows:
        name = r.get("name", "")
        s_match = s_pattern.search(name)
        e_match = e_pattern.search(name)
        if s_match:
            has_s += 1
            season_numbers[int(s_match.group(1))] += 1
        else:
            no_s += 1
            if len(examples_no_s) < 10:
                examples_no_s.append(name)
        if e_match:
            has_e += 1

    report["total"] = len(rows)
    report["has_season_number"] = has_s
    report["has_episode_number_in_name"] = has_e
    report["no_season_number"] = no_s
    report["no_season_examples"] = examples_no_s
    report["season_number_distribution"] = dict(sorted(season_numbers.items()))
    return report


def extract_episode_name_structure(rows: list[dict]) -> dict:
    """从子节目 name 中提取季/集号"""
    import re

    s_pattern = re.compile(r"S(\d{1,3})", re.IGNORECASE)
    e_pattern = re.compile(r"E(\d{1,3})", re.IGNORECASE)

    season_numbers = Counter()
    episode_numbers = Counter()
    has_s = 0
    has_e = 0
    no_s = 0
    no_e = 0
    examples_no_s = []
    examples_no_e = []

    for r in rows:
        name = r.get("name", "")
        s_match = s_pattern.search(name)
        e_match = e_pattern.search(name)
        if s_match:
            has_s += 1
            season_numbers[int(s_match.group(1))] += 1
        else:
            no_s += 1
            if len(examples_no_s) < 10:
                examples_no_s.append(name)
        if e_match:
            has_e += 1
            episode_numbers[int(e_match.group(1))] += 1
        else:
            no_e += 1
            if len(examples_no_e) < 10:
                examples_no_e.append(name)

    return {
        "total": len(rows),
        "has_season_number": has_s,
        "has_episode_number": has_e,
        "no_season_number": no_s,
        "no_season_examples": examples_no_s,
        "no_episode_number": no_e,
        "no_episode_examples": examples_no_e,
        "season_number_distribution": dict(sorted(season_numbers.items())),
        "episode_number_top30": dict(episode_numbers.most_common(30)),
    }


def main():
    print("=" * 72)
    print("A 库 CSV 解析验证")
    print("=" * 72)

    # 1. 加载
    print("\n[1/5] 加载 CSV ...")
    prog_cols, prog_rows = load_csv(PROGRAM_CSV)
    ep_cols, ep_rows = load_csv(EPISODE_CSV)
    print(f"  节目数据: {len(prog_rows)} 行 × {len(prog_cols)} 列")
    print(f"  子节目数据: {len(ep_rows)} 行 × {len(ep_cols)} 列")

    # 2. 节目表分析
    print("\n[2/5] 节目表分析 ...")
    prog_report = analyse_programs(prog_rows)
    print(f"  program_status 分布: {prog_report['program_status_distribution']}")
    print(f"  imdb_id 填充率: {prog_report['imdb_id_fill_rate']}")
    print(f"  make_year 填充率: {prog_report['make_year_fill_rate']}")
    print(f"  delete_flag 分布: {prog_report['delete_flag_distribution']}")
    print(f"  online_flag 分布: {prog_report['online_flag_distribution']}")
    print(f"  tenant_id 分布: {prog_report['tenant_id_distribution']}")

    # 3. 子节目表分析
    print("\n[3/5] 子节目表分析 ...")
    ep_report = analyse_episodes(ep_rows)
    print(f"  video_status 分布: {ep_report['video_status_distribution']}")
    print(f"  source_type 分布: {ep_report['source_type_distribution']}")
    print(f"  pc_type 分布 (父节目类型): {ep_report['pc_type_distribution']}")
    print(f"  pc_program_status 分布: {ep_report['pc_program_status_distribution']}")
    print(f"  pc_imdb_id 填充率: {ep_report['pc_imdb_id_fill_rate']}")
    print(f"  fk_program_content_id 填充率: {ep_report['fk_program_content_id_fill_rate']}")
    print(f"  去重子节目 ID: {ep_report['unique_id_count']}")
    print(f"  去重父节目数: {ep_report['total_unique_parents']}")
    print(f"  平均每节目子节目数: {ep_report['avg_children_per_parent']}")

    # 4. 关联分析
    print("\n[4/5] 关联分析 ...")
    cross = cross_analysis(prog_rows, ep_rows)
    print(f"  节目表 ID 总数: {cross['total_program_ids']}")
    print(f"  子节目中引用的去重父 ID 数: {cross['unique_fk_program_content_ids_in_episodes']}")
    print(f"  匹配成功: {cross['matched_parent_ids']}")
    print(f"  孤儿引用 (子节目有但节目表无): {cross['orphan_parent_ids_in_episodes']}")
    if cross["orphan_examples"]:
        print(f"  孤儿示例: {cross['orphan_examples']}")
    print(f"  未被引用的节目数: {cross['unreferenced_programs']}")
    if cross["unreferenced_examples"]:
        print(f"  孤独节目示例: {cross['unreferenced_examples'][:5]}")
    print(f"  pc_name vs 节目.name 不一致数: {cross['pc_name_vs_program_name_mismatches']}")
    if cross["mismatch_examples"]:
        for ex in cross["mismatch_examples"][:3]:
            print(f"    不一致: pc_name='{ex['pc_name']}' vs prog_name='{ex['program_name']}'")

    # 5. 命名模式提取
    print("\n[5/5] 命名模式分析 ...")
    prog_name_rpt = extract_program_name_structure(prog_rows)
    print(f"  节目名含 S\d\d: {prog_name_rpt['has_season_number']}/{prog_name_rpt['total']}")
    print(f"  节目名含 E\d\d: {prog_name_rpt['has_episode_number_in_name']}/{prog_name_rpt['total']}")
    print(f"  节目名无季号: {prog_name_rpt['no_season_number']}")
    if prog_name_rpt["no_season_examples"]:
        print(f"  无季号示例: {prog_name_rpt['no_season_examples'][:5]}")

    ep_name_rpt = extract_episode_name_structure(ep_rows)
    print(f"  子节目名含 S\d\d: {ep_name_rpt['has_season_number']}/{ep_name_rpt['total']}")
    print(f"  子节目名含 E\d\d: {ep_name_rpt['has_episode_number']}/{ep_name_rpt['total']}")
    if ep_name_rpt["no_season_examples"]:
        print(f"  子节目无季号示例: {ep_name_rpt['no_season_examples'][:5]}")
    if ep_name_rpt["no_episode_examples"]:
        print(f"  子节目无集号示例: {ep_name_rpt['no_episode_examples'][:5]}")

    print("\n" + "=" * 72)
    print("验证完成。")
    print("=" * 72)


if __name__ == "__main__":
    main()
