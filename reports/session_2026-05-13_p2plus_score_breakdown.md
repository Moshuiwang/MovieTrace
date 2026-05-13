# P2+ 候选评分详情报告

- [ ] 报告已审阅，可归档

**生成时间：** 2026-05-13 22:31 +08
**数据日期：** 2026-05-13
**数据来源：** 当前 `data/movietrace.db` 中的 FlixPatrol / TMDb / Trakt 表 + 本地 `api_cache`
**说明：** 本报告重新计算评分，不访问外部 API；用于解释 P2 及以上候选为什么得分未进一步升高。

---

## 评分规则速读

当前 hot_score 是 9 个因子的加权总分，满分 100：

| 因子 | 权重 | 说明 |
|------|------|------|
| FP | 30% | 原始因子分 0-100 后乘以权重 |
| TMDb热度 | 15% | 原始因子分 0-100 后乘以权重 |
| Trakt | 10% | 原始因子分 0-100 后乘以权重 |
| TMDb评分 | 10% | 原始因子分 0-100 后乘以权重 |
| IMDb评分 | 10% | 原始因子分 0-100 后乘以权重 |
| 平台 | 10% | 原始因子分 0-100 后乘以权重 |
| 类型 | 5% | 原始因子分 0-100 后乘以权重 |
| 新鲜度 | 5% | 原始因子分 0-100 后乘以权重 |
| 语言 | 5% | 原始因子分 0-100 后乘以权重 |

优先级阈值：`P0 >= 85`，`P1 >= 70`，`P2 >= 50`。

读表方法：表里的因子分都是 0-100 的原始分，不是加权后的贡献分。例如 `FP=100` 在总分中贡献 30 分。

---

## 总览

- 全部候选：724
- P2+ 候选：62（P0=1，P1=6，P2=55）
- 本地 OMDb 缓存命中并应用：588
- 本地 TMDb detail 缓存命中并应用：564

### 分数段

| 分数段 | 数量 |
|--------|------|
| 85+ | 1 |
| 80-84.9 | 1 |
| 75-79.9 | 0 |
| 70-74.9 | 5 |
| 60-69.9 | 25 |
| 50-59.9 | 30 |

### P2+ 常见扣分原因

| 扣分原因 | 命中条数 |
|----------|----------|
| TMDb热度低/缺 | 60 |
| Trakt热度低/缺 | 57 |
| 非近期内容 | 41 |
| TMDb评分/票数不够强 | 27 |
| FP弱或缺失 | 21 |
| IMDb缺失 | 19 |
| 非英语/语言未知 | 2 |

解读：P0/P1 少的核心原因是多数候选只有部分强信号。FP 恢复后能把候选推到 P2，但要进 P1/P0，通常还需要 TMDb / Trakt / IMDb / 新鲜度同时较强。

---

## P2+ 全量评分明细

| # | 优先级 | 分数 | 标题 | 类型 | 来源 | FP榜单 | FP | TMDb热度 | Trakt | TMDb评分 | IMDb评分 | 新鲜度 | 主要加分 | 主要扣分/未升档原因 |
|---|--------|------|------|------|------|--------|----|----------|-------|----------|----------|--------|----------|----------------------|
| 1 | P0 | 88.5 | The Boys | tv | FP+TMDb+Trakt+IMDb | prime-video #1, 34d | 100 | 57 | 100 | 100 | 100 | 0 | FP+30.0, TMDb热度+8.5, Trakt+10.0, TMDb评分+10.0 | 已达P0；非近期内容 |
| 2 | P1 | 82.6 | Euphoria | tv | FP+TMDb+Trakt+IMDb | hbo-max #1, 53d | 100 | 27 | 100 | 100 | 100 | 0 | FP+30.0, Trakt+10.0, TMDb评分+10.0, IMDb评分+10.0 | 距P0差 2.4；TMDb热度低/缺；非近期内容 |
| 3 | P1 | 74.7 | INVINCIBLE | tv | FP+TMDb+Trakt+IMDb | prime-video #3, 55d | 100 | 12 | 29 | 100 | 100 | 0 | FP+30.0, TMDb评分+10.0, IMDb评分+10.0, 平台+10.0 | 距P0差 10.3；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 4 | P1 | 73.0 | The Devil Wears Prada | movie | FP+TMDb+Trakt+IMDb | disney-plus #1, 25d | 100 | 28 | 7 | 100 | 100 | 0 | FP+30.0, TMDb评分+10.0, IMDb评分+10.0, 平台+9.0 | 距P0差 12.0；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 5 | P1 | 72.3 | Daredevil: Born Again | tv | FP+TMDb+Trakt+IMDb | disney-plus #3, 25d | 97 | 11 | 47 | 80 | 100 | 0 | FP+29.0, IMDb评分+10.0, 平台+9.0 | 距P0差 12.7；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 6 | P1 | 70.6 | Rooster | tv | FP+TMDb+Trakt+IMDb | hbo-max #2, 64d | 100 | 3 | 54 | 44 | 70 | 100 | FP+30.0, 平台+8.5 | 距P0差 14.4；TMDb热度低/缺；IMDb评分/票数不够强；TMDb评分/票数不够强 |
| 7 | P1 | 70.5 | Star Wars: Maul - Shadow Lord | tv | FP+TMDb+Trakt+IMDb | disney-plus #1, 25d | 100 | 4 | 21 | 60 | 78 | 100 | FP+30.0, 平台+9.0 | 距P0差 14.5；TMDb热度低/缺；Trakt热度低/缺；TMDb评分/票数不够强 |
| 8 | P2 | 69.6 | Send Help | movie | FP+TMDb+Trakt+IMDb | hulu #1, 5d | 100 | 23 | 9 | 74 | 84 | 50 | FP+30.0, IMDb评分+8.4, 平台+8.0 | 距P1差 0.4；TMDb热度低/缺；Trakt热度低/缺 |
| 9 | P2 | 69.4 | Swapped | movie | FP+TMDb+Trakt | netflix #2, 11d | 97 | 44 | 11 | 85 | - | 100 | FP+29.2, TMDb评分+8.5, 平台+10.0 | 距P1差 0.6；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失 |
| 10 | P2 | 68.6 | Last Week Tonight with John Oliver | tv | FP+TMDb+Trakt+IMDb | hbo-max #3, 545d | 100 | 2 | 22 | 76 | 100 | 0 | FP+30.0, IMDb评分+10.0, 平台+8.5 | 距P1差 1.4；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 11 | P2 | 68.0 | Grey's Anatomy | tv | FP+TMDb+Trakt+IMDb | hulu #5, 340d | 80 | 23 | 25 | 100 | 100 | 0 | FP+24.0, TMDb评分+10.0, IMDb评分+10.0, 平台+8.0 | 距P1差 2.0；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 12 | P2 | 67.9 | Your Friends & Neighbors | tv | FP+TMDb+Trakt+IMDb | apple-tv-plus #1, 175d | 100 | 4 | 44 | 59 | 90 | 0 | FP+30.0, IMDb评分+9.0, 平台+8.0 | 距P1差 2.1；TMDb热度低/缺；Trakt热度低/缺；TMDb评分/票数不够强；非近期内容 |
| 13 | P2 | 67.1 | F1 | movie | FP+TMDb+Trakt+IMDb | apple-tv-plus #2, 152d | 100 | 4 | 2 | 93 | 100 | 0 | FP+30.0, TMDb评分+9.3, IMDb评分+10.0, 平台+8.0 | 距P1差 2.9；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 14 | P2 | 67.0 | 9-1-1 | tv | FP+TMDb+Trakt+IMDb | hulu #4, 363d | 90 | 9 | 18 | 94 | 95 | 0 | FP+27.0, TMDb评分+9.4, IMDb评分+9.5, 平台+8.0 | 距P1差 3.0；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 15 | P2 | 66.1 | The Testaments | tv | FP+TMDb+Trakt+IMDb | hulu #2, 34d | 100 | 4 | 16 | 44 | 66 | 100 | FP+30.0, 平台+8.0 | 距P1差 3.9；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强；TMDb评分/票数不够强 |
| 16 | P2 | 66.0 | Citadel | tv | FP+TMDb+Trakt+IMDb | prime-video #2, 6d | 94 | 9 | 32 | 62 | 71 | 0 | FP+28.2, 平台+10.0 | 距P1差 4.0；TMDb热度低/缺；Trakt热度低/缺；TMDb评分/票数不够强；非近期内容 |
| 17 | P2 | 65.8 | Ted Lasso | tv | FP+TMDb+Trakt+IMDb | apple-tv-plus #4, 837d | 90 | 3 | 9 | 94 | 100 | 0 | FP+27.0, TMDb评分+9.4, IMDb评分+10.0, 平台+8.0 | 距P1差 4.2；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 18 | P2 | 65.4 | Margo's Got Money Troubles | tv | FP+TMDb+Trakt+IMDb | apple-tv-plus #2, 28d | 100 | 4 | 25 | 44 | 50 | 100 | FP+30.0, 平台+8.0 | 距P1差 4.6；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强；TMDb评分/票数不够强 |
| 19 | P2 | 64.7 | Family Guy | tv | FP+TMDb+Trakt+IMDb | hulu #6, 416d | 70 | 14 | 44 | 91 | 100 | 0 | FP+21.0, TMDb评分+9.1, IMDb评分+10.0, 平台+8.0 | 距P1差 5.3；FP不在头部(hulu #6, 416d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 20 | P2 | 64.6 | Hacks | tv | FP+TMDb+Trakt+IMDb | hbo-max #4, 150d | 90 | 4 | 23 | 63 | 98 | 0 | FP+27.0, IMDb评分+9.8, 平台+8.5 | 距P1差 5.4；TMDb热度低/缺；Trakt热度低/缺；TMDb评分/票数不够强；非近期内容 |
| 21 | P2 | 63.9 | "Wuthering Heights" | movie | FP+TMDb+Trakt+IMDb | hbo-max #2, 10d | 97 | 5 | 3 | 65 | 74 | 50 | FP+29.0, 平台+8.5 | 距P1差 6.1；TMDb热度低/缺；Trakt热度低/缺；TMDb评分/票数不够强 |
| 22 | P2 | 63.6 | Remarkably Bright Creatures | movie | FP+TMDb+Trakt | netflix #1, 4d | 100 | 14 | 14 | 60 | - | 100 | FP+30.0, 平台+10.0 | 距P1差 6.4；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；TMDb评分/票数不够强 |
| 23 | P2 | 63.4 | Greenland 2: Migration | movie | FP+TMDb+Trakt+IMDb | hbo-max #1, 3d | 100 | 7 | 3 | 64 | 58 | 50 | FP+30.0, 平台+8.5 | 距P1差 6.6；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强；TMDb评分/票数不够强 |
| 24 | P2 | 63.2 | Greenland | movie | FP+TMDb+Trakt+IMDb | hbo-max #3, 21d | 94 | 1 | 1 | 88 | 83 | 0 | FP+28.2, TMDb评分+8.8, IMDb评分+8.3, 平台+8.5 | 距P1差 6.8；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 25 | P2 | 63.0 | Marty Supreme | movie | FP+TMDb+Trakt+IMDb | hbo-max #4, 17d | 81 | 2 | 3 | 80 | 100 | 50 | FP+24.4, IMDb评分+10.0, 平台+8.5 | 距P1差 7.0；TMDb热度低/缺；Trakt热度低/缺 |
| 26 | P2 | 62.5 | Raw | tv | FP+TMDb+Trakt+IMDb | netflix #2, 1d | 91 | 7 | 6 | 58 | 79 | 0 | FP+27.2, 平台+10.0 | 距P1差 7.5；TMDb热度低/缺；Trakt热度低/缺；TMDb评分/票数不够强；非近期内容 |
| 27 | P2 | 61.6 | Regretting You | movie | FP+TMDb+IMDb | prime-video #1, 11d | 100 | 1 | - | 60 | 64 | 0 | FP+30.0, 平台+10.0 | 距P1差 8.4；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强；TMDb评分/票数不够强 |
| 28 | P2 | 61.6 | The Rookie | tv | FP+TMDb+Trakt+IMDb | hulu #8, 387d | 50 | 28 | 44 | 100 | 100 | 0 | FP+15.0, TMDb评分+10.0, IMDb评分+10.0, 平台+8.0 | 距P1差 8.4；FP不在头部(hulu #8, 387d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 29 | P2 | 61.5 | For All Mankind | tv | FP+TMDb+Trakt+IMDb | apple-tv-plus #6, 508d | 70 | 5 | 41 | 76 | 100 | 0 | FP+21.0, IMDb评分+10.0, 平台+8.0 | 距P1差 8.5；FP不在头部(apple-tv-plus #6, 508d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 30 | P2 | 61.4 | Shrinking | tv | FP+TMDb+Trakt+IMDb | apple-tv-plus #5, 690d | 80 | 3 | 16 | 73 | 100 | 0 | FP+24.0, IMDb评分+10.0, 平台+8.0 | 距P1差 8.6；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 31 | P2 | 61.1 | Worst Ex Ever | tv | FP+TMDb+Trakt+IMDb | netflix #3, 34d | 100 | 1 | 5 | 40 | 64 | 0 | FP+30.0, 平台+10.0 | 距P1差 8.9；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强；TMDb评分/票数不够强 |
| 32 | P2 | 60.6 | Outcome | movie | FP+TMDb+Trakt+IMDb | apple-tv-plus #1, 33d | 100 | 2 | 1 | 40 | 42 | 100 | FP+30.0, 平台+8.0 | 距P1差 9.4；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强；TMDb评分/票数不够强 |
| 33 | P2 | 58.5 | Apex | movie | FP+TMDb+Trakt | netflix #5, 18d | 72 | 31 | 17 | 65 | - | 100 | FP+21.6, 平台+10.0 | 距P1差 11.5；FP不在头部(netflix #5, 18d)；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失 |
| 34 | P2 | 57.7 | Widow's Bay | tv | FP+TMDb+Trakt | apple-tv-plus #3, 14d | 89 | 4 | 32 | 41 | - | 100 | FP+26.8, 平台+8.0 | 距P1差 12.3；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；TMDb评分/票数不够强 |
| 35 | P2 | 57.6 | Vengeance | movie | FP+TMDb | prime-video #3, 18d | 92 | 12 | - | 52 | - | 100 | FP+27.6, 平台+10.0 | 距P1差 12.4；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；TMDb评分/票数不够强 |
| 36 | P2 | 57.5 | Mortal Kombat | movie | FP+TMDb+Trakt+IMDb | hbo-max #5, 13d | 69 | 12 | 7 | 89 | 81 | 0 | FP+20.6, TMDb评分+8.9, IMDb评分+8.1, 平台+8.5 | 距P1差 12.5；FP不在头部(hbo-max #5, 13d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 37 | P2 | 57.3 | Bob's Burgers | tv | FP+TMDb+Trakt+IMDb | hulu #7, 388d | 60 | 5 | 27 | 79 | 100 | 0 | FP+18.0, IMDb评分+10.0, 平台+8.0 | 距P1差 12.7；FP不在头部(hulu #7, 388d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 38 | P2 | 57.2 | Scarpetta | tv | FP+TMDb+Trakt+IMDb | prime-video #6, 62d | 70 | 2 | 3 | 44 | 63 | 100 | FP+21.0, 平台+10.0 | 距P1差 12.8；FP不在头部(prime-video #6, 62d)；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强 |
| 39 | P2 | 56.9 | FROM | tv | TMDb+Trakt+IMDb | - | 0 | 61 | 100 | 97 | 100 | 0 | TMDb热度+9.2, Trakt+10.0, TMDb评分+9.7, IMDb评分+10.0 | 距P1差 13.1；无FP信号；非近期内容 |
| 40 | P2 | 55.8 | Man on Fire | tv | FP+TMDb+Trakt | netflix #4, 12d | 78 | 5 | 21 | 46 | - | 100 | FP+23.4, 平台+10.0 | 距P1差 14.2；FP不在头部(netflix #4, 12d)；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失 |
| 41 | P2 | 55.8 | Greyhound | movie | FP+TMDb | apple-tv-plus #3, 683d | 100 | 1 | - | 87 | - | 0 | FP+30.0, TMDb评分+8.7, 平台+8.0 | 距P1差 14.2；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；非近期内容 |
| 42 | P2 | 55.1 | La Brea | tv | FP+TMDb+Trakt+IMDb | netflix #5, 11d | 67 | 3 | 2 | 79 | 63 | 0 | FP+20.2, 平台+10.0 | 距P1差 14.9；FP不在头部(netflix #5, 11d)；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强 |
| 43 | P2 | 54.3 | Home | movie | FP+TMDb | netflix #4, 87d | 90 | 1 | - | 82 | - | 0 | FP+27.0, TMDb评分+8.2, 平台+10.0 | 距P1差 15.7；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；非近期内容 |
| 44 | P2 | 53.8 | The Pitt | tv | FP+TMDb+Trakt+IMDb | hbo-max #9, 263d | 40 | 6 | 40 | 83 | 100 | 0 | FP+12.0, TMDb评分+8.3, IMDb评分+10.0, 平台+8.5 | 距P1差 16.2；FP不在头部(hbo-max #9, 263d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 45 | P2 | 53.5 | The Gorge | movie | FP+TMDb | apple-tv-plus #4, 432d | 90 | 3 | - | 90 | - | 0 | FP+27.0, TMDb评分+9.1, 平台+8.0 | 距P1差 16.5；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；非近期内容 |
| 46 | P2 | 53.1 | Deadpool & Wolverine | movie | FP+TMDb+Trakt+IMDb | disney-plus #7, 13d | 49 | 3 | 1 | 99 | 100 | 0 | FP+14.6, TMDb评分+9.9, IMDb评分+10.0, 平台+9.0 | 距P1差 16.9；FP不在头部(disney-plus #7, 13d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 47 | P2 | 53.1 | Project Hail Mary | movie | TMDb+Trakt+IMDb | - | 0 | 37 | 60 | 96 | 100 | 100 | TMDb评分+9.6, IMDb评分+10.0, 平台+8.0 | 距P1差 16.9；无FP信号；TMDb热度低/缺 |
| 48 | P2 | 52.8 | Balls Up | movie | FP+TMDb+Trakt | prime-video #5, 27d | 78 | 5 | 2 | 45 | - | 100 | FP+23.4, 平台+10.0 | 距P1差 17.2；FP不在头部(prime-video #5, 27d)；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失 |
| 49 | P2 | 52.8 | Fallout | tv | FP+TMDb+Trakt+IMDb | prime-video #9, 146d | 40 | 3 | 10 | 93 | 100 | 0 | FP+12.0, TMDb评分+9.3, IMDb评分+10.0, 平台+10.0 | 距P1差 17.2；FP不在头部(prime-video #9, 146d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 50 | P2 | 52.8 | White Chicks | movie | FP+TMDb | hulu #4, 49d | 90 | 2 | - | 84 | - | 0 | FP+27.0, TMDb评分+8.4, 平台+8.0 | 距P1差 17.2；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；非近期内容 |
| 51 | P2 | 52.7 | Monarch: Legacy of Monsters | tv | FP+TMDb+Trakt+IMDb | apple-tv-plus #8, 294d | 50 | 7 | 23 | 80 | 84 | 0 | FP+15.0, IMDb评分+8.3, 平台+8.0 | 距P1差 17.3；FP不在头部(apple-tv-plus #8, 294d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 52 | P2 | 52.6 | Spider-Man: No Way Home | movie | FP+TMDb+Trakt | disney-plus #3, 0d | 80 | 3 | 1 | 100 | - | 0 | FP+24.0, TMDb评分+10.0, 平台+9.0 | 距P1差 17.4；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；非近期内容 |
| 53 | P2 | 52.6 | The Mandalorian | tv | FP+TMDb+Trakt+IMDb | disney-plus #8, 15d | 40 | 6 | 8 | 100 | 100 | 0 | FP+12.0, TMDb评分+10.0, IMDb评分+10.0, 平台+9.0 | 距P1差 17.4；FP不在头部(disney-plus #8, 15d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 54 | P2 | 52.6 | General Hospital | tv | FP+TMDb | hulu #1, 721d | 100 | 1 | - | 45 | - | 0 | FP+30.0, 平台+8.0 | 距P1差 17.4；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；TMDb评分/票数不够强 |
| 55 | P2 | 52.3 | Bang | movie | FP+TMDb | prime-video #2, 17d | 100 | 1 | - | 42 | - | 0 | FP+30.0, 平台+10.0 | 距P1差 17.7；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；TMDb评分/票数不够强 |
| 56 | P2 | 52.3 | The House of the Spirits | tv | FP+TMDb+Trakt | prime-video #4, 11d | 77 | 2 | 2 | 36 | - | 100 | FP+23.2, 平台+10.0 | 距P1差 17.7；FP不在头部(prime-video #4, 11d)；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失 |
| 57 | P2 | 51.4 | 20/20 | tv | FP+TMDb | hulu #3, 528d | 100 | 1 | - | 33 | - | 0 | FP+30.0, 平台+8.0 | 距P1差 18.6；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；TMDb评分/票数不够强 |
| 58 | P2 | 50.9 | Tom Clancy's Jack Ryan | tv | FP+TMDb+Trakt+IMDb | prime-video #8, 14d | 39 | 4 | 2 | 83 | 100 | 0 | FP+11.8, TMDb评分+8.3, IMDb评分+10.0, 平台+10.0 | 距P1差 19.1；FP不在头部(prime-video #8, 14d)；TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 59 | P2 | 50.6 | Lord of the Flies | tv | FP+TMDb+Trakt+IMDb | netflix #6, 8d | 55 | 3 | 5 | 46 | 59 | 50 | FP+16.6, 平台+10.0 | 距P1差 19.4；FP不在头部(netflix #6, 8d)；TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强 |
| 60 | P2 | 50.5 | Star Wars: Episode I - The Phantom Menace | movie | FP+TMDb+Trakt | disney-plus #4, 10d | 77 | 1 | 1 | 92 | - | 0 | FP+23.0, TMDb评分+9.2, 平台+9.0 | 距P1差 19.5；FP不在头部(disney-plus #4, 10d)；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失 |
| 61 | P2 | 50.2 | Mother's Day | movie | FP+TMDb | netflix #3, 4d | 83 | 1 | - | 62 | - | 0 | FP+24.8, 平台+10.0 | 距P1差 19.8；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；TMDb评分/票数不够强 |
| 62 | P2 | 50.2 | Eternity | movie | FP+TMDb | apple-tv-plus #5, 89d | 80 | 1 | - | 66 | - | 50 | FP+24.0, 平台+8.0 | 距P1差 19.8；TMDb热度低/缺；Trakt热度低/缺；IMDb缺失；TMDb评分/票数不够强 |

---

## 重点观察

### 最接近 P1 的 P2 候选

这些条目通常只差一个强信号，例如 IMDb 可用、Trakt 更高、或新鲜度更高，就可能进入 P1。

| 标题 | 分数 | 距P1 | 主要短板 |
|------|------|------|----------|
| Send Help | 69.6 | 0.4 | TMDb热度低/缺；Trakt热度低/缺 |
| Swapped | 69.4 | 0.6 | TMDb热度低/缺；Trakt热度低/缺；IMDb缺失 |
| Last Week Tonight with John Oliver | 68.6 | 1.4 | TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| Grey's Anatomy | 68.0 | 2.0 | TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| Your Friends & Neighbors | 67.9 | 2.1 | TMDb热度低/缺；Trakt热度低/缺；TMDb评分/票数不够强；非近期内容 |
| F1 | 67.1 | 2.9 | TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| 9-1-1 | 67.0 | 3.0 | TMDb热度低/缺；Trakt热度低/缺；非近期内容 |
| The Testaments | 66.1 | 3.9 | TMDb热度低/缺；Trakt热度低/缺；IMDb评分/票数不够强；TMDb评分/票数不够强 |
| Citadel | 66.0 | 4.0 | TMDb热度低/缺；Trakt热度低/缺；TMDb评分/票数不够强；非近期内容 |
| Ted Lasso | 65.8 | 4.2 | TMDb热度低/缺；Trakt热度低/缺；非近期内容 |

### 为什么很多 P2 没有升到 P1/P0

1. **FP 只占 30 分。** 即使某内容在 FP 排名第一，仍需要其他源共同支撑。
2. **TMDb / Trakt 热度分布很陡。** 许多内容有 TMDb 或 Trakt 信号，但没有达到高热度归一化上限。
3. **IMDb 缺失或缓存未命中会直接少最多 10 分。** 本次端到端验证已观察到 OMDb `401 Unauthorized`，新条目富化存在风险。
4. **非近期内容新鲜度为 0。** 流媒体 Top 10 常有老片、回流剧、家庭片，能上 P2，但很难冲 P0/P1。
5. **P0/P1 当前定义偏严格。** P1 要求总分 70，P0 要求 85，基本等价于多源强共振。

---

## 剩余风险

- [ ] 本报告使用本地缓存解释 IMDb / TMDb detail；如果 OMDb 401 修复后重新富化，部分条目的 IMDb 分可能变化。
- [ ] 本报告只解释当前评分结果，不提出或执行权重调整。权重调整应进入单独 Phase 1.8 任务包。
- [ ] `dry-run` 不写入 discovery 类 `content_updates`，本报告基于重新计算的候选，不等同于已入库推荐清单。
