# 项目状态快照

> 冷启动回答：现在停在哪儿 / 有没有阻塞 / 下一步。
> 历史 → `git log` + `docs/tasks/p1.*.md` + [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)
> DB schema → [`.claude/rules/24-db-schema-map.md`](.claude/rules/24-db-schema-map.md) · 日常运行 → [`docs/operations/runbook.md`](docs/operations/runbook.md)

**最后更新：** 2026-05-24 · 分支 `refactor/p1.56-architecture-adjustments`
**测试：** 835 passed · **Schema：** v19

---

## 现在停在哪儿

Phase 0 → 1.55 全部上线（P1.17 跳过 / P1.22 预留 V2 episode 级）。P1.57a-n current discovery 改造（[ADR-0016](docs/decisions/0016-current-discovery-with-observations.md)）本地完成；开发分支 shadow cron 观察期 2026-05-24 → 2026-05-31，观察结束后整批 PR。P1.56 pipeline 阶段契约暂缓，要求已吸收到 P1.57d/j。

## 进行中 / 阻塞 / 待决策

- **进行中：** P1.57k 一周 shadow cron 观察期；观察结束后整批 PR（含 m/n review fix）
- **阻塞：** FlixPatrol API 订阅 402（脚本走合规公开页面 fallback，无业务影响）
- **待决策：** 无

## Issues

GitHub issues #4-#8 关闭；#9（IMDB 源头）OPEN 但 V2 backlog（合规跳过）。
