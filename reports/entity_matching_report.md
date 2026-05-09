# MovieTrace 实体匹配样本报告

状态：Phase 0 正式验证产物
生成时间：2026-05-09 16:29:09 +0800
数据来源：飞书 `节目` 表前 100 条非空节目名样本
外部数据源：TMDb search/multi、Trakt search/movie,show
写入范围：只读取飞书正式表，不写入或修改正式表

## 1. 结论摘要

- 样本数量：100 条。
- 解析出季号的标题：94 条，占 94.0%。
- 带备注的样本：0 条，占 0.0%。
- high 匹配：100 条，占 100.0%。
- medium 匹配：0 条，占 0.0%。
- low 匹配：0 条，占 0.0%。
- no_match：0 条，占 0.0%。
- high + medium 合计：100 条，占 100.0%。

初步判断：当前标题可以支持一部分实体匹配验证，但由于缺少年份、内容类型、季集结构和外部 ID，`medium` 以下结果不能用于自动去重，只能进入人工确认。

## 2. 匹配规则

- 先从本地标题解析 `Sxx` 季号，例如 `Silo S01` -> season 1。
- 搜索时移除 `Sxx` 和年份，得到基础标题。
- TMDb 使用 `search/multi`，仅保留 movie / tv。
- Trakt 使用 `search/movie,show`，避免使用本次验证中曾触发 403 的 `extended=full`。
- high：标题高度相似，且 TMDb / Trakt 外部 ID 交叉一致，或标题近乎完全一致且季号提示与 TV 类型一致。
- medium：标题相似度较高，但缺少足够消歧字段。
- low：存在可能匹配，但标题或类型有明显不确定性。
- no_match：未找到可靠外部结果。

## 3. API 状态

- TMDb 与 Trakt 样本搜索均返回 HTTP 200。

## 4. 样本匹配明细

| # | 本地标题 | 解析标题 | 季号 | 置信度 | 最佳来源 | 外部标题 | 类型 | 年份 | TMDb ID | IMDb ID | 相似度 | 依据 |
| ---: | --- | --- | ---: | --- | --- | --- | --- | ---: | --- | --- | ---: | --- |
| 1 | Avatar The Way of Water | avatar the way of water |  | high | tmdb | Avatar: The Way of Water | movie | 2022 | 76600 |  | 1.00 | title_similarity=1.00; tmdb_trakt_cross_id_match |
| 2 | From S02 | from | 2 | high | tmdb | FROM | tv | 2022 | 124364 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 3 | Narappa | narappa |  | high | tmdb | Narappa | movie | 2021 | 666564 |  | 1.00 | title_similarity=1.00; tmdb_trakt_cross_id_match |
| 4 | Never Have I Ever S01 | never have i ever | 1 | high | tmdb | Never Have I Ever | tv | 2020 | 100883 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 5 | Never Have I Ever S02 | never have i ever | 2 | high | tmdb | Never Have I Ever | tv | 2020 | 100883 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 6 | Never Have I Ever S03 | never have i ever | 3 | high | tmdb | Never Have I Ever | tv | 2020 | 100883 |  | 1.00 | title_similarity=1.00; parsed_season=S03; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 7 | Never Have I Ever S04 | never have i ever | 4 | high | tmdb | Never Have I Ever | tv | 2020 | 100883 |  | 1.00 | title_similarity=1.00; parsed_season=S04; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 8 | Platonic S01 | platonic | 1 | high | tmdb | Platonic | tv | 2023 | 112211 |  | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 9 | Silo S01 | silo | 1 | high | tmdb | Silo | tv | 2023 | 125988 |  | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 10 | The Crowded Room S01 | the crowded room | 1 | high | tmdb | The Crowded Room | tv | 2023 | 123192 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 11 | The Idol S01 | the idol | 1 | high | tmdb | The Idol | tv | 2023 | 135251 |  | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 12 | The Lake S01 | the lake | 1 | high | tmdb | The Lake | tv | 2022 | 158051 |  | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 13 | The Lake S02 | the lake | 2 | high | tmdb | The Lake | tv | 2022 | 158051 |  | 1.00 | title_similarity=1.00; parsed_season=S02; season_hint_matches_tv |
| 14 | American Born Chinese S01 | american born chinese | 1 | high | tmdb | American Born Chinese | tv | 2023 | 135615 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 15 | CSI Vegas S02 | csi vegas | 2 | high | tmdb | CSI: Vegas | tv | 2021 | 122194 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 16 | I Survived a Crime S01 | i survived a crime | 1 | high | tmdb | I Survived a Crime | tv | 2021 | 119896 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 17 | John Wick Chapter 4 | john wick chapter 4 |  | high | tmdb | John Wick: Chapter 4 | movie | 2023 | 603692 |  | 1.00 | title_similarity=1.00; tmdb_trakt_cross_id_match |
| 18 | Dear Mama S01 | dear mama | 1 | high | tmdb | Dear Mama | tv | 2023 | 201581 |  | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 19 | Fear the Walking Dead S08 | fear the walking dead | 8 | high | tmdb | Fear the Walking Dead | tv | 2015 | 62286 |  | 1.00 | title_similarity=1.00; parsed_season=S08; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 20 | Let's Get Divorced S01 | let s get divorced | 1 | high | tmdb | Let's Get Divorced | tv | 2023 | 216223 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 21 | The Blue Caftan | the blue caftan |  | high | tmdb | The Blue Caftan | movie | 2023 | 958279 |  | 1.00 | title_similarity=1.00; tmdb_trakt_cross_id_match |
| 22 | The Cable Guy | the cable guy |  | high | tmdb | The Cable Guy | movie | 1996 | 9894 |  | 1.00 | title_similarity=1.00; tmdb_trakt_cross_id_match |
| 23 | Better Call Saul S01 | better call saul | 1 | high | tmdb | Better Call Saul | tv | 2015 | 60059 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 24 | Better Call Saul S02 | better call saul | 2 | high | tmdb | Better Call Saul | tv | 2015 | 60059 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 25 | Better Call Saul S03 | better call saul | 3 | high | tmdb | Better Call Saul | tv | 2015 | 60059 |  | 1.00 | title_similarity=1.00; parsed_season=S03; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 26 | Better Call Saul S04 | better call saul | 4 | high | tmdb | Better Call Saul | tv | 2015 | 60059 |  | 1.00 | title_similarity=1.00; parsed_season=S04; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 27 | Sherlock S01 | sherlock | 1 | high | tmdb | Sherlock | tv | 2010 | 19885 |  | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 28 | Sherlock S02 | sherlock | 2 | high | tmdb | Sherlock | tv | 2010 | 19885 |  | 1.00 | title_similarity=1.00; parsed_season=S02; season_hint_matches_tv |
| 29 | Sherlock S03 | sherlock | 3 | high | tmdb | Sherlock | tv | 2010 | 19885 |  | 1.00 | title_similarity=1.00; parsed_season=S03; season_hint_matches_tv |
| 30 | Sherlock S04 | sherlock | 4 | high | tmdb | Sherlock | tv | 2010 | 19885 |  | 1.00 | title_similarity=1.00; parsed_season=S04; season_hint_matches_tv |
| 31 | Friends S01 | friends | 1 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 32 | Friends S02 | friends | 2 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S02; season_hint_matches_tv |
| 33 | Friends S03 | friends | 3 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S03; season_hint_matches_tv |
| 34 | Friends S04 | friends | 4 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S04; season_hint_matches_tv |
| 35 | Friends S05 | friends | 5 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S05; season_hint_matches_tv |
| 36 | Friends S06 | friends | 6 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S06; season_hint_matches_tv |
| 37 | Friends S07 | friends | 7 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S07; season_hint_matches_tv |
| 38 | Friends S08 | friends | 8 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S08; season_hint_matches_tv |
| 39 | Friends S09 | friends | 9 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S09; season_hint_matches_tv |
| 40 | Friends S10 | friends | 10 | high | tmdb | Friends | tv | 1994 | 1668 |  | 1.00 | title_similarity=1.00; parsed_season=S10; season_hint_matches_tv |
| 41 | Game of Thrones S01 | game of thrones | 1 | high | tmdb | Game of Thrones | tv | 2011 | 1399 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 42 | Game of Thrones S02 | game of thrones | 2 | high | tmdb | Game of Thrones | tv | 2011 | 1399 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 43 | Game of Thrones S03 | game of thrones | 3 | high | tmdb | Game of Thrones | tv | 2011 | 1399 |  | 1.00 | title_similarity=1.00; parsed_season=S03; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 44 | Game of Thrones S04 | game of thrones | 4 | high | tmdb | Game of Thrones | tv | 2011 | 1399 |  | 1.00 | title_similarity=1.00; parsed_season=S04; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 45 | Game of Thrones S05 | game of thrones | 5 | high | tmdb | Game of Thrones | tv | 2011 | 1399 |  | 1.00 | title_similarity=1.00; parsed_season=S05; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 46 | Game of Thrones S06 | game of thrones | 6 | high | tmdb | Game of Thrones | tv | 2011 | 1399 |  | 1.00 | title_similarity=1.00; parsed_season=S06; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 47 | Game of Thrones S07 | game of thrones | 7 | high | tmdb | Game of Thrones | tv | 2011 | 1399 |  | 1.00 | title_similarity=1.00; parsed_season=S07; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 48 | BoJack Horseman S01 | bojack horseman | 1 | high | tmdb | BoJack Horseman | tv | 2014 | 61222 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 49 | BoJack Horseman S02 | bojack horseman | 2 | high | tmdb | BoJack Horseman | tv | 2014 | 61222 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 50 | BoJack Horseman S03 | bojack horseman | 3 | high | tmdb | BoJack Horseman | tv | 2014 | 61222 |  | 1.00 | title_similarity=1.00; parsed_season=S03; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 51 | BoJack Horseman S04 | bojack horseman | 4 | high | tmdb | BoJack Horseman | tv | 2014 | 61222 |  | 1.00 | title_similarity=1.00; parsed_season=S04; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 52 | BoJack Horseman S05 | bojack horseman | 5 | high | tmdb | BoJack Horseman | tv | 2014 | 61222 |  | 1.00 | title_similarity=1.00; parsed_season=S05; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 53 | The Big Bang Theory S01 | the big bang theory | 1 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 54 | The Big Bang Theory S02 | the big bang theory | 2 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 55 | The Big Bang Theory S03 | the big bang theory | 3 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S03; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 56 | The Big Bang Theory S04 | the big bang theory | 4 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S04; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 57 | The Big Bang Theory S05 | the big bang theory | 5 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S05; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 58 | The Big Bang Theory S06 | the big bang theory | 6 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S06; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 59 | The Big Bang Theory S07 | the big bang theory | 7 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S07; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 60 | The Big Bang Theory S08 | the big bang theory | 8 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S08; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 61 | The Big Bang Theory S09 | the big bang theory | 9 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S09; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 62 | The Big Bang Theory S10 | the big bang theory | 10 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S10; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 63 | The Big Bang Theory S11 | the big bang theory | 11 | high | tmdb | The Big Bang Theory | tv | 2007 | 1418 |  | 1.00 | title_similarity=1.00; parsed_season=S11; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 64 | The Night Of S01 | the night of | 1 | high | trakt | The Night Of | tv | 2016 | 66276 | tt2401256 | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 65 | Modern Family S01 | modern family | 1 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 66 | Modern Family S02 | modern family | 2 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 67 | Modern Family S03 | modern family | 3 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S03; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 68 | Modern Family S04 | modern family | 4 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S04; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 69 | Modern Family S05 | modern family | 5 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S05; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 70 | Modern Family S06 | modern family | 6 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S06; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 71 | Modern Family S07 | modern family | 7 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S07; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 72 | Modern Family S08 | modern family | 8 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S08; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 73 | Modern Family S09 | modern family | 9 | high | tmdb | Modern Family | tv | 2009 | 1421 |  | 1.00 | title_similarity=1.00; parsed_season=S09; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 74 | Orange Is the New Black S01 | orange is the new black | 1 | high | tmdb | Orange Is the New Black | tv | 2013 | 1424 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 75 | Orange Is the New Black S02 | orange is the new black | 2 | high | tmdb | Orange Is the New Black | tv | 2013 | 1424 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 76 | Orange Is the New Black S03 | orange is the new black | 3 | high | tmdb | Orange Is the New Black | tv | 2013 | 1424 |  | 1.00 | title_similarity=1.00; parsed_season=S03; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 77 | Orange Is the New Black S04 | orange is the new black | 4 | high | tmdb | Orange Is the New Black | tv | 2013 | 1424 |  | 1.00 | title_similarity=1.00; parsed_season=S04; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 78 | Orange Is the New Black S05 | orange is the new black | 5 | high | tmdb | Orange Is the New Black | tv | 2013 | 1424 |  | 1.00 | title_similarity=1.00; parsed_season=S05; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 79 | Orange Is the New Black S06 | orange is the new black | 6 | high | tmdb | Orange Is the New Black | tv | 2013 | 1424 |  | 1.00 | title_similarity=1.00; parsed_season=S06; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 80 | The Blacklist S01 | the blacklist | 1 | high | tmdb | The Blacklist | tv | 2013 | 46952 |  | 1.00 | title_similarity=1.00; parsed_season=S01; season_hint_matches_tv |
| 81 | The Blacklist S02 | the blacklist | 2 | high | tmdb | The Blacklist | tv | 2013 | 46952 |  | 1.00 | title_similarity=1.00; parsed_season=S02; season_hint_matches_tv |
| 82 | The Blacklist S03 | the blacklist | 3 | high | tmdb | The Blacklist | tv | 2013 | 46952 |  | 1.00 | title_similarity=1.00; parsed_season=S03; season_hint_matches_tv |
| 83 | The Blacklist S04 | the blacklist | 4 | high | tmdb | The Blacklist | tv | 2013 | 46952 |  | 1.00 | title_similarity=1.00; parsed_season=S04; season_hint_matches_tv |
| 84 | The Blacklist S05 | the blacklist | 5 | high | tmdb | The Blacklist | tv | 2013 | 46952 |  | 1.00 | title_similarity=1.00; parsed_season=S05; season_hint_matches_tv |
| 85 | Alice in Borderland S01 | alice in borderland | 1 | high | tmdb | Alice in Borderland | tv | 2020 | 110316 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 86 | Alice in Borderland S02 | alice in borderland | 2 | high | tmdb | Alice in Borderland | tv | 2020 | 110316 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 87 | All of Us Are Dead S01 | all of us are dead | 1 | high | tmdb | All of Us Are Dead | tv | 2022 | 99966 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 88 | American Horror Story S01 | american horror story | 1 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 89 | American Horror Story S02 | american horror story | 2 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S02; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 90 | American Horror Story S03 | american horror story | 3 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S03; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 91 | American Horror Story S04 | american horror story | 4 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S04; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 92 | American Horror Story S05 | american horror story | 5 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S05; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 93 | American Horror Story S06 | american horror story | 6 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S06; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 94 | American Horror Story S07 | american horror story | 7 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S07; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 95 | American Horror Story S08 | american horror story | 8 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S08; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 96 | American Horror Story S09 | american horror story | 9 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S09; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 97 | American Horror Story S10 | american horror story | 10 | high | tmdb | American Horror Story | tv | 2011 | 1413 |  | 1.00 | title_similarity=1.00; parsed_season=S10; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 98 | Behind Her Eyes S01 | behind her eyes | 1 | high | tmdb | Behind Her Eyes | tv | 2021 | 97173 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |
| 99 | Band of Brothers | band of brothers |  | high | tmdb | Band of Brothers | tv | 2001 | 4613 |  | 1.00 | title_similarity=1.00; tmdb_trakt_cross_id_match |
| 100 | Black Mirror S01 | black mirror | 1 | high | tmdb | Black Mirror | tv | 2011 | 42009 |  | 1.00 | title_similarity=1.00; parsed_season=S01; tmdb_trakt_cross_id_match; season_hint_matches_tv |

## 5. 风险与建议

1. 当前样本匹配仍依赖标题，缺少年份和内容类型时，同名电影/剧集有误匹配风险。
2. 标题中包含 `Sxx` 的记录可以提示 TV/season，但不能单独证明该季已上架。
3. Trakt 搜索在使用 `extended=full` 时曾返回 403/error 1010，后续实现应默认不用该参数，必要时单独重试。
4. 后续完整节目库导出应优先补充 `content_type`、`content_granularity`、`year` 和外部 ID。
5. high 匹配可以作为候选自动补 ID 的起点，但在进入业务过滤前仍建议抽样人工复核。

## 6. 下一步

建议人工复核本报告中的 high / medium 样本，统计高置信度准确率。如果 high 准确率达到 95% 以上，再扩大到 300 条样本或全量标题匹配 dry run。
