# MovieTrace 全量实体匹配报告

生成时间：2026-05-10 13:29:35 Asia/Shanghai
状态：Phase 0 验证产物
数据来源：本地 SQLite `baseline_items`
写入范围：本地 `match_candidates`，不写飞书正式表

## 1. 结论摘要

- 基线记录数：855
- 匹配候选记录数：853
- API 错误数：2

| 置信度 | 数量 | 占比 |
| --- | ---: | ---: |
| high | 779 | 91.1% |
| medium | 73 | 8.5% |
| low | 1 | 0.1% |
| no_match | 2 | 0.2% |

## 2. 低置信度和未匹配样本

| baseline_item_id | 本地标题 | 搜索标题 | 置信度 | 外部标题 | 来源 | 年份 | 依据 |
| ---: | --- | --- | --- | --- | --- | ---: | --- |
| 410 | Scout's Honor The Secret Files of the Boy Scouts of America S01 | Scout's Honor The Secret Files of the Boy Scouts of America | no_match |  |  |  | api_error=RuntimeError: TraktSearchClient:HTTPError |
| 770 | The Vienna Boys' Choir Silk Songs Along The Road And Time | The Vienna Boys' Choir Silk Songs Along The Road And Time | no_match |  |  |  | api_error=RuntimeError: TraktSearchClient:HTTPError |
| 847 | Special Ops Lioness S01 | Special Ops Lioness | low | Lioness | tmdb | 2023 | title_similarity=0.54; matched_field=title; parsed_season=S01; season_hint_matches_tv; tmdb=Lioness\|tv\|2023\|low |

## 3. TMDB / OMDb 全量建议与差异

TMDB ID 与 IMDb ID 属于不同编号体系，不参与冲突判断。差异仅基于标题、类型、年份和来源置信度。

| baseline_item_id | 本地标题 | 搜索标题 | 最终置信度 | 最终候选 | TMDB ID | IMDb ID | TMDB 建议 | OMDb 建议 | 差异 |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Avatar The Way of Water | Avatar The Way of Water | high | Avatar: The Way of Water movie 2022 high | 76600 | tt1630029 | Avatar: The Way of Water movie 2022 high | Avatar: The Way of Water movie 2022 high | compatible |
| 2 | From S02 | From | high | FROM tv 2022 high | 124364 | tt9813792 | FROM tv 2022 high | From tv 2022 high | compatible |
| 3 | Narappa | Narappa | high | Narappa movie 2021 high | 666564 | tt11648514 | Narappa movie 2021 high | Narappa movie 2021 high | compatible |
| 4 | Never Have I Ever S01 | Never Have I Ever | high | Never Have I Ever tv 2020 high | 100883 | tt10062292 | Never Have I Ever tv 2020 high | Never Have I Ever tv 2020 high | compatible |
| 5 | Never Have I Ever S02 | Never Have I Ever | high | Never Have I Ever tv 2020 high | 100883 | tt10062292 | Never Have I Ever tv 2020 high | Never Have I Ever tv 2020 high | compatible |
| 6 | Never Have I Ever S03 | Never Have I Ever | high | Never Have I Ever tv 2020 high | 100883 | tt10062292 | Never Have I Ever tv 2020 high | Never Have I Ever tv 2020 high | compatible |
| 7 | Never Have I Ever S04 | Never Have I Ever | high | Never Have I Ever tv 2020 high | 100883 | tt10062292 | Never Have I Ever tv 2020 high | Never Have I Ever tv 2020 high | compatible |
| 8 | Platonic S01 | Platonic | high | Platonic tv 2023 high | 112211 | tt13366604 | Platonic tv 2023 high | Platonic tv 2023 high | compatible |
| 9 | Silo S01 | Silo | high | Silo tv 2023 high | 125988 | tt14688458 | Silo tv 2023 high | Silo tv 2023 high | compatible |
| 10 | The Crowded Room S01 | The Crowded Room | high | The Crowded Room tv 2023 high | 123192 | tt14417718 | The Crowded Room tv 2023 high | The Crowded Room tv 2023 high | compatible |
| 11 | The Idol S01 | The Idol | high | The Idol tv 2023 high | 135251 | tt14954666 | The Idol tv 2023 high | The Idol tv 2023 high | compatible |
| 12 | The Lake S01 | The Lake | high | The Lake tv 2022 high | 158051 | tt15176890 | The Lake tv 2022 high | The Lake tv 2022 high | compatible |
| 13 | The Lake S02 | The Lake | high | The Lake tv 2022 high | 158051 | tt15176890 | The Lake tv 2022 high | The Lake tv 2022 high | compatible |
| 14 | American Born Chinese S01 | American Born Chinese | high | American Born Chinese tv 2023 high | 135615 | tt15552018 | American Born Chinese tv 2023 high | American Born Chinese tv 2023 high | compatible |
| 15 | CSI Vegas S02 | CSI Vegas | high | CSI: Vegas tv 2021 high | 122194 | tt12887536 | CSI: Vegas tv 2021 high | CSI: Vegas tv 2021 high | compatible |
| 16 | I Survived a Crime S01 | I Survived a Crime | high | I Survived a Crime tv 2021 high | 119896 | tt13471702 | I Survived a Crime tv 2021 high | I Survived a Crime tv 2021 high | compatible |
| 17 | John Wick Chapter 4 | John Wick Chapter 4 | high | John Wick: Chapter 4 movie 2023 high | 603692 | tt10366206 | John Wick: Chapter 4 movie 2023 high | John Wick: Chapter 4 movie 2023 high | compatible |
| 18 | Dear Mama S01 | Dear Mama | high | Dear Mama tv 2023 high | 201581 | tt6871344 | Dear Mama tv 2023 high | Dear Mama tv 2022 high | compatible |
| 19 | Fear the Walking Dead S08 | Fear the Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 20 | Let's Get Divorced S01 | Let's Get Divorced | high | Let's Get Divorced tv 2023 high | 216223 | tt15567320 | Let's Get Divorced tv 2023 high | Let's Get Divorced tv 2023 high | compatible |
| 21 | The Blue Caftan | The Blue Caftan | high | The Blue Caftan movie 2023 high | 958279 | tt17679584 | The Blue Caftan movie 2023 high | The Blue Caftan movie 2022 high | compatible |
| 22 | The Cable Guy | The Cable Guy | medium | The Cable Guy movie 1996 medium | 9894 | tt10328022 | The Cable Guy movie 1996 high | The Cable Guy movie 2018 high | year_delta=22 |
| 23 | Better Call Saul S01 | Better Call Saul | high | Better Call Saul tv 2015 high | 60059 | tt3032476 | Better Call Saul tv 2015 high | Better Call Saul tv 2015 high | compatible |
| 24 | Better Call Saul S02 | Better Call Saul | high | Better Call Saul tv 2015 high | 60059 | tt3032476 | Better Call Saul tv 2015 high | Better Call Saul tv 2015 high | compatible |
| 25 | Better Call Saul S03 | Better Call Saul | high | Better Call Saul tv 2015 high | 60059 | tt3032476 | Better Call Saul tv 2015 high | Better Call Saul tv 2015 high | compatible |
| 26 | Better Call Saul S04 | Better Call Saul | high | Better Call Saul tv 2015 high | 60059 | tt3032476 | Better Call Saul tv 2015 high | Better Call Saul tv 2015 high | compatible |
| 27 | Sherlock S01 | Sherlock | medium | SHErlock tv 2023 medium | 224755 | tt1475582 | SHErlock tv 2023 high | Sherlock tv 2010 high | year_delta=13 |
| 28 | Sherlock S02 | Sherlock | medium | SHErlock tv 2023 medium | 224755 | tt1475582 | SHErlock tv 2023 high | Sherlock tv 2010 high | year_delta=13 |
| 29 | Sherlock S03 | Sherlock | medium | SHErlock tv 2023 medium | 224755 | tt1475582 | SHErlock tv 2023 high | Sherlock tv 2010 high | year_delta=13 |
| 30 | Sherlock S04 | Sherlock | medium | SHErlock tv 2023 medium | 224755 | tt1475582 | SHErlock tv 2023 high | Sherlock tv 2010 high | year_delta=13 |
| 31 | Friends S01 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 32 | Friends S02 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 33 | Friends S03 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 34 | Friends S04 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 35 | Friends S05 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 36 | Friends S06 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 37 | Friends S07 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 38 | Friends S08 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 39 | Friends S09 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 40 | Friends S10 | Friends | high | Smiling Friends tv 2020 high | 126506 | tt12074628 | Smiling Friends tv 2020 high | Smiling Friends tv 2020 high | compatible |
| 41 | Game of Thrones S01 | Game of Thrones | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 42 | Game of Thrones S02 | Game of Thrones | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 43 | Game of Thrones S03 | Game of Thrones | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 44 | Game of Thrones S04 | Game of Thrones | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 45 | Game of Thrones S05 | Game of Thrones | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 46 | Game of Thrones S06 | Game of Thrones | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 47 | Game of Thrones S07 | Game of Thrones | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 48 | BoJack Horseman S01 | BoJack Horseman | high | BoJack Horseman tv 2014 high | 61222 | tt3398228 | BoJack Horseman tv 2014 high | BoJack Horseman tv 2014 high | compatible |
| 49 | BoJack Horseman S02 | BoJack Horseman | high | BoJack Horseman tv 2014 high | 61222 | tt3398228 | BoJack Horseman tv 2014 high | BoJack Horseman tv 2014 high | compatible |
| 50 | BoJack Horseman S03 | BoJack Horseman | high | BoJack Horseman tv 2014 high | 61222 | tt3398228 | BoJack Horseman tv 2014 high | BoJack Horseman tv 2014 high | compatible |
| 51 | BoJack Horseman S04 | BoJack Horseman | high | BoJack Horseman tv 2014 high | 61222 | tt3398228 | BoJack Horseman tv 2014 high | BoJack Horseman tv 2014 high | compatible |
| 52 | BoJack Horseman S05 | BoJack Horseman | high | BoJack Horseman tv 2014 high | 61222 | tt3398228 | BoJack Horseman tv 2014 high | BoJack Horseman tv 2014 high | compatible |
| 53 | The Big Bang Theory S01 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 54 | The Big Bang Theory S02 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 55 | The Big Bang Theory S03 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 56 | The Big Bang Theory S04 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 57 | The Big Bang Theory S05 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 58 | The Big Bang Theory S06 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 59 | The Big Bang Theory S07 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 60 | The Big Bang Theory S08 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 61 | The Big Bang Theory S09 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 62 | The Big Bang Theory S10 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 63 | The Big Bang Theory S11 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 64 | The Night Of S01 | The Night Of | high | The Night Of tv 2016 high | 66276 | tt2401256 | The Night Of tv 2016 high | The Night Of tv 2016 high | compatible |
| 65 | Modern Family S01 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 66 | Modern Family S02 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 67 | Modern Family S03 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 68 | Modern Family S04 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 69 | Modern Family S05 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 70 | Modern Family S06 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 71 | Modern Family S07 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 72 | Modern Family S08 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 73 | Modern Family S09 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 74 | Orange Is the New Black S01 | Orange Is the New Black | high | Orange Is the New Black tv 2013 high | 1424 | tt2372162 | Orange Is the New Black tv 2013 high | Orange Is the New Black tv 2013 high | compatible |
| 75 | Orange Is the New Black S02 | Orange Is the New Black | high | Orange Is the New Black tv 2013 high | 1424 | tt2372162 | Orange Is the New Black tv 2013 high | Orange Is the New Black tv 2013 high | compatible |
| 76 | Orange Is the New Black S03 | Orange Is the New Black | high | Orange Is the New Black tv 2013 high | 1424 | tt2372162 | Orange Is the New Black tv 2013 high | Orange Is the New Black tv 2013 high | compatible |
| 77 | Orange Is the New Black S04 | Orange Is the New Black | high | Orange Is the New Black tv 2013 high | 1424 | tt2372162 | Orange Is the New Black tv 2013 high | Orange Is the New Black tv 2013 high | compatible |
| 78 | Orange Is the New Black S05 | Orange Is the New Black | high | Orange Is the New Black tv 2013 high | 1424 | tt2372162 | Orange Is the New Black tv 2013 high | Orange Is the New Black tv 2013 high | compatible |
| 79 | Orange Is the New Black S06 | Orange Is the New Black | high | Orange Is the New Black tv 2013 high | 1424 | tt2372162 | Orange Is the New Black tv 2013 high | Orange Is the New Black tv 2013 high | compatible |
| 80 | The Blacklist S01 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 81 | The Blacklist S02 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 82 | The Blacklist S03 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 83 | The Blacklist S04 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 84 | The Blacklist S05 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 85 | Alice in Borderland S01 | Alice in Borderland | high | Alice in Borderland tv 2020 high | 110316 | tt10795658 | Alice in Borderland tv 2020 high | Alice in Borderland tv 2020 high | compatible |
| 86 | Alice in Borderland S02 | Alice in Borderland | high | Alice in Borderland tv 2020 high | 110316 | tt10795658 | Alice in Borderland tv 2020 high | Alice in Borderland tv 2020 high | compatible |
| 87 | All of Us Are Dead S01 | All of Us Are Dead | high | All of Us Are Dead tv 2022 high | 99966 | tt14169960 | All of Us Are Dead tv 2022 high | All of Us Are Dead tv 2022 high | compatible |
| 88 | American Horror Story S01 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 89 | American Horror Story S02 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 90 | American Horror Story S03 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 91 | American Horror Story S04 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 92 | American Horror Story S05 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 93 | American Horror Story S06 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 94 | American Horror Story S07 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 95 | American Horror Story S08 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 96 | American Horror Story S09 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 97 | American Horror Story S10 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 98 | Behind Her Eyes S01 | Behind Her Eyes | high | Behind Her Eyes tv 2021 high | 97173 | tt9698442 | Behind Her Eyes tv 2021 high | Behind Her Eyes tv 2021 high | compatible |
| 99 | Band of Brothers | Band of Brothers | medium | Band of Brothers movie 2019 medium | 484744 | tt14148100 | Band of Brothers movie 2019 high | Gold Rush: Band of Brothers movie 2021 high | year_delta=2,title_diff |
| 100 | Black Mirror S01 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 101 | Black Mirror S02 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 102 | Black Mirror S03 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 103 | Black Mirror S04 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 104 | Black Mirror S05 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 105 | Black Mirror S06 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 106 | Boardwalk Empire S01 | Boardwalk Empire | high | Boardwalk Empire tv 2010 high | 1621 | tt0979432 | Boardwalk Empire tv 2010 high | Boardwalk Empire tv 2010 high | compatible |
| 107 | Boardwalk Empire S02 | Boardwalk Empire | high | Boardwalk Empire tv 2010 high | 1621 | tt0979432 | Boardwalk Empire tv 2010 high | Boardwalk Empire tv 2010 high | compatible |
| 108 | Boardwalk Empire S03 | Boardwalk Empire | high | Boardwalk Empire tv 2010 high | 1621 | tt0979432 | Boardwalk Empire tv 2010 high | Boardwalk Empire tv 2010 high | compatible |
| 109 | Boardwalk Empire S04 | Boardwalk Empire | high | Boardwalk Empire tv 2010 high | 1621 | tt0979432 | Boardwalk Empire tv 2010 high | Boardwalk Empire tv 2010 high | compatible |
| 110 | Boardwalk Empire S05 | Boardwalk Empire | high | Boardwalk Empire tv 2010 high | 1621 | tt0979432 | Boardwalk Empire tv 2010 high | Boardwalk Empire tv 2010 high | compatible |
| 111 | Agents of S.H.I.E.L.D. S01 | Agents of S.H.I.E.L.D. | high | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | 1403 | tt2364582 | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | Agents of S.H.I.E.L.D. tv 2013 high | compatible |
| 112 | Agents of S.H.I.E.L.D. S02 | Agents of S.H.I.E.L.D. | high | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | 1403 | tt2364582 | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | Agents of S.H.I.E.L.D. tv 2013 high | compatible |
| 113 | Agents of S.H.I.E.L.D. S03 | Agents of S.H.I.E.L.D. | high | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | 1403 | tt2364582 | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | Agents of S.H.I.E.L.D. tv 2013 high | compatible |
| 114 | Agents of S.H.I.E.L.D. S04 | Agents of S.H.I.E.L.D. | high | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | 1403 | tt2364582 | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | Agents of S.H.I.E.L.D. tv 2013 high | compatible |
| 115 | Agents of S.H.I.E.L.D. S05 | Agents of S.H.I.E.L.D. | high | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | 1403 | tt2364582 | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | Agents of S.H.I.E.L.D. tv 2013 high | compatible |
| 116 | Agents of S.H.I.E.L.D. S06 | Agents of S.H.I.E.L.D. | high | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | 1403 | tt2364582 | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | Agents of S.H.I.E.L.D. tv 2013 high | compatible |
| 117 | Agents of S.H.I.E.L.D. S07 | Agents of S.H.I.E.L.D. | high | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | 1403 | tt2364582 | Marvel's Agents of S.H.I.E.L.D. tv 2013 high | Agents of S.H.I.E.L.D. tv 2013 high | compatible |
| 118 | Billions S01 | Billions | high | Billions tv 2016 high | 62852 | tt4270492 | Billions tv 2016 high | Billions tv 2016 high | compatible |
| 119 | Billions S02 | Billions | high | Billions tv 2016 high | 62852 | tt4270492 | Billions tv 2016 high | Billions tv 2016 high | compatible |
| 120 | Billions S03 | Billions | high | Billions tv 2016 high | 62852 | tt4270492 | Billions tv 2016 high | Billions tv 2016 high | compatible |
| 121 | Billions S04 | Billions | high | Billions tv 2016 high | 62852 | tt4270492 | Billions tv 2016 high | Billions tv 2016 high | compatible |
| 122 | Billions S05 | Billions | high | Billions tv 2016 high | 62852 | tt4270492 | Billions tv 2016 high | Billions tv 2016 high | compatible |
| 123 | Billions S06 | Billions | high | Billions tv 2016 high | 62852 | tt4270492 | Billions tv 2016 high | Billions tv 2016 high | compatible |
| 124 | Better Call Saul S05 | Better Call Saul | high | Better Call Saul tv 2015 high | 60059 | tt3032476 | Better Call Saul tv 2015 high | Better Call Saul tv 2015 high | compatible |
| 125 | Better Call Saul S06 | Better Call Saul | high | Better Call Saul tv 2015 high | 60059 | tt3032476 | Better Call Saul tv 2015 high | Better Call Saul tv 2015 high | compatible |
| 126 | Bridgerton S01 | Bridgerton | high | Bridgerton tv 2020 high | 91239 | tt8740790 | Bridgerton tv 2020 high | Bridgerton tv 2020 high | compatible |
| 127 | Bridgerton S02 | Bridgerton | high | Bridgerton tv 2020 high | 91239 | tt8740790 | Bridgerton tv 2020 high | Bridgerton tv 2020 high | compatible |
| 128 | Business Proposal S01 | Business Proposal | high | Business Proposal tv 2022 high | 154825 | tt14819828 | Business Proposal tv 2022 high | Business Proposal tv 2022 high | compatible |
| 129 | Dahmer - Monster The Jeffrey Dahmer Story S01 | Dahmer - Monster The Jeffrey Dahmer Story | high | DAHMER - Monster: The Jeffrey Dahmer Story tv 2022 high | 113988 |  | DAHMER - Monster: The Jeffrey Dahmer Story tv 2022 high | none no_match no_external_result | tmdb_only |
| 130 | Dark S01 | Dark | high | Dark tv 2017 high | 70523 | tt5753856 | Dark tv 2017 high | Dark tv 2017 high | compatible |
| 131 | Dark S02 | Dark | high | Dark tv 2017 high | 70523 | tt5753856 | Dark tv 2017 high | Dark tv 2017 high | compatible |
| 132 | Dark S03 | Dark | high | Dark tv 2017 high | 70523 | tt5753856 | Dark tv 2017 high | Dark tv 2017 high | compatible |
| 133 | Dead to Me S01 | Dead to Me | high | Dead to Me tv 2019 high | 81357 | tt8064302 | Dead to Me tv 2019 high | Dead to Me tv 2019 high | compatible |
| 134 | Dead to Me S02 | Dead to Me | high | Dead to Me tv 2019 high | 81357 | tt8064302 | Dead to Me tv 2019 high | Dead to Me tv 2019 high | compatible |
| 135 | Dead to Me S03 | Dead to Me | high | Dead to Me tv 2019 high | 81357 | tt8064302 | Dead to Me tv 2019 high | Dead to Me tv 2019 high | compatible |
| 136 | Enola Holmes 2 | Enola Holmes 2 | high | Enola Holmes 2 movie 2022 high | 829280 | tt14641788 | Enola Holmes 2 movie 2022 high | Enola Holmes 2 movie 2022 high | compatible |
| 137 | Extraordinary Attorney Woo S01 | Extraordinary Attorney Woo | high | Extraordinary Attorney Woo tv 2022 high | 197067 | tt20869502 | Extraordinary Attorney Woo tv 2022 high | Extraordinary Attorney Woo tv 2022 high | compatible |
| 138 | Foundation S01 | Foundation | high | Foundation tv 2021 high | 93740 | tt0804484 | Foundation tv 2021 high | Foundation tv 2021 high | compatible |
| 139 | Foundation S02 | Foundation | high | Foundation tv 2021 high | 93740 | tt0804484 | Foundation tv 2021 high | Foundation tv 2021 high | compatible |
| 140 | Ginny %26 Georgia S01 | Ginny & Georgia | high | Ginny & Georgia tv 2021 high | 117581 | tt10813940 | Ginny & Georgia tv 2021 high | Ginny & Georgia tv 2021 high | compatible |
| 141 | Ginny %26 Georgia S02 | Ginny & Georgia | high | Ginny & Georgia tv 2021 high | 117581 | tt10813940 | Ginny & Georgia tv 2021 high | Ginny & Georgia tv 2021 high | compatible |
| 142 | Gossip Girl S01 | Gossip Girl | high | Gossip Girl tv 2021 high | 95249 | tt10653784 | Gossip Girl tv 2021 high | Gossip Girl tv 2021 high | compatible |
| 143 | Gossip Girl S02 | Gossip Girl | high | Gossip Girl tv 2021 high | 95249 | tt10653784 | Gossip Girl tv 2021 high | Gossip Girl tv 2021 high | compatible |
| 144 | Gossip Girl S03 | Gossip Girl | high | Gossip Girl tv 2021 high | 95249 | tt10653784 | Gossip Girl tv 2021 high | Gossip Girl tv 2021 high | compatible |
| 145 | Gossip Girl S04 | Gossip Girl | high | Gossip Girl tv 2021 high | 95249 | tt10653784 | Gossip Girl tv 2021 high | Gossip Girl tv 2021 high | compatible |
| 146 | Gossip Girl S05 | Gossip Girl | high | Gossip Girl tv 2021 high | 95249 | tt10653784 | Gossip Girl tv 2021 high | Gossip Girl tv 2021 high | compatible |
| 147 | Gossip Girl S06 | Gossip Girl | high | Gossip Girl tv 2021 high | 95249 | tt10653784 | Gossip Girl tv 2021 high | Gossip Girl tv 2021 high | compatible |
| 148 | Hollywood S01 | Hollywood | high | Hollywood tv 2020 high | 87050 | tt9827854 | Hollywood tv 2020 high | Hollywood tv 2020 high | compatible |
| 149 | Inventing Anna S01 | Inventing Anna | high | Inventing Anna tv 2022 high | 95665 | tt8740976 | Inventing Anna tv 2022 high | Inventing Anna tv 2022 high | compatible |
| 150 | Kaleidoscope S01 | Kaleidoscope | high | Kaleidoscope tv 2023 high | 156902 | tt15438246 | Kaleidoscope tv 2023 high | Kaleidoscope tv 2023 high | compatible |
| 151 | Love%2C Death %26 Robots S01 | Love, Death & Robots | high | Love, Death & Robots tv 2019 high | 86831 | tt9561862 | Love, Death & Robots tv 2019 high | Love, Death & Robots tv 2019 high | compatible |
| 152 | Love%2C Death %26 Robots S02 | Love, Death & Robots | high | Love, Death & Robots tv 2019 high | 86831 | tt9561862 | Love, Death & Robots tv 2019 high | Love, Death & Robots tv 2019 high | compatible |
| 153 | Love%2C Death %26 Robots S03 | Love, Death & Robots | high | Love, Death & Robots tv 2019 high | 86831 | tt9561862 | Love, Death & Robots tv 2019 high | Love, Death & Robots tv 2019 high | compatible |
| 154 | Lupin S01 | Lupin | high | Lupin tv 2021 high | 96677 | tt2531336 | Lupin tv 2021 high | Lupin tv 2021 high | compatible |
| 155 | Lupin S02 | Lupin | high | Lupin tv 2021 high | 96677 | tt2531336 | Lupin tv 2021 high | Lupin tv 2021 high | compatible |
| 156 | Maid S01 | Maid | high | Maid tv 2021 high | 111141 | tt11337908 | Maid tv 2021 high | Maid tv 2021 high | compatible |
| 157 | Move to Heaven S01 | Move to Heaven | high | Move to Heaven tv 2021 high | 96571 | tt11052470 | Move to Heaven tv 2021 high | Move to Heaven tv 2021 high | compatible |
| 158 | Narcos S01 | Narcos | high | Narcos tv 2015 high | 63351 | tt2707408 | Narcos tv 2015 high | Narcos tv 2015 high | compatible |
| 159 | Narcos S02 | Narcos | high | Narcos tv 2015 high | 63351 | tt2707408 | Narcos tv 2015 high | Narcos tv 2015 high | compatible |
| 160 | Narcos S03 | Narcos | high | Narcos tv 2015 high | 63351 | tt2707408 | Narcos tv 2015 high | Narcos tv 2015 high | compatible |
| 161 | New Amsterdam S01 | New Amsterdam | high | New Amsterdam tv 2018 high | 80350 | tt7817340 | New Amsterdam tv 2018 high | New Amsterdam tv 2018 high | compatible |
| 162 | New Amsterdam S02 | New Amsterdam | high | New Amsterdam tv 2018 high | 80350 | tt7817340 | New Amsterdam tv 2018 high | New Amsterdam tv 2018 high | compatible |
| 163 | New Amsterdam S03 | New Amsterdam | high | New Amsterdam tv 2018 high | 80350 | tt7817340 | New Amsterdam tv 2018 high | New Amsterdam tv 2018 high | compatible |
| 164 | New Amsterdam S04 | New Amsterdam | high | New Amsterdam tv 2018 high | 80350 | tt7817340 | New Amsterdam tv 2018 high | New Amsterdam tv 2018 high | compatible |
| 165 | New Amsterdam S05 | New Amsterdam | high | New Amsterdam tv 2018 high | 80350 | tt7817340 | New Amsterdam tv 2018 high | New Amsterdam tv 2018 high | compatible |
| 166 | Nine Perfect Strangers S01 | Nine Perfect Strangers | high | Nine Perfect Strangers tv 2021 high | 88989 | tt8760932 | Nine Perfect Strangers tv 2021 high | Nine Perfect Strangers tv 2021 high | compatible |
| 167 | Our Planet S01 | Our Planet | medium | Life on Our Planet tv 2023 medium | 213609 | tt9253866 | Life on Our Planet tv 2023 high | Our Planet tv 2019 high | year_delta=4,title_diff |
| 168 | Our Planet S02 | Our Planet | medium | Life on Our Planet tv 2023 medium | 213609 | tt9253866 | Life on Our Planet tv 2023 high | Our Planet tv 2019 high | year_delta=4,title_diff |
| 169 | Oz S01 | Oz | high | Oz tv 1997 high | 3322 |  | Oz tv 1997 high | none no_match no_external_result | tmdb_only |
| 170 | Oz S02 | Oz | high | Oz tv 1997 high | 3322 |  | Oz tv 1997 high | none no_match no_external_result | tmdb_only |
| 171 | Oz S03 | Oz | high | Oz tv 1997 high | 3322 |  | Oz tv 1997 high | none no_match no_external_result | tmdb_only |
| 172 | Oz S04 | Oz | high | Oz tv 1997 high | 3322 |  | Oz tv 1997 high | none no_match no_external_result | tmdb_only |
| 173 | Oz S05 | Oz | high | Oz tv 1997 high | 3322 |  | Oz tv 1997 high | none no_match no_external_result | tmdb_only |
| 174 | Oz S06 | Oz | high | Oz tv 1997 high | 3322 |  | Oz tv 1997 high | none no_match no_external_result | tmdb_only |
| 175 | Purple Hearts | Purple Hearts | high | Purple Hearts movie 2022 high | 762975 | tt4614584 | Purple Hearts movie 2022 high | Purple Hearts movie 2022 high | compatible |
| 176 | Sense8 S01 | Sense8 | high | Sense8 tv 2015 high | 61664 | tt2431438 | Sense8 tv 2015 high | Sense8 tv 2015 high | compatible |
| 177 | Sense8 S02 | Sense8 | high | Sense8 tv 2015 high | 61664 | tt2431438 | Sense8 tv 2015 high | Sense8 tv 2015 high | compatible |
| 178 | Sex Education S01 | Sex Education | high | Sex Education tv 2019 high | 81356 | tt7767422 | Sex Education tv 2019 high | Sex Education tv 2019 high | compatible |
| 179 | Sex Education S02 | Sex Education | high | Sex Education tv 2019 high | 81356 | tt7767422 | Sex Education tv 2019 high | Sex Education tv 2019 high | compatible |
| 180 | Sex Education S03 | Sex Education | high | Sex Education tv 2019 high | 81356 | tt7767422 | Sex Education tv 2019 high | Sex Education tv 2019 high | compatible |
| 181 | Sex Life S01 | Sex Life | high | Sex/Life tv 2021 high | 126280 | tt10839422 | Sex/Life tv 2021 high | Sex/Life tv 2021 high | compatible |
| 182 | Sex Life S02 | Sex Life | high | Sex/Life tv 2021 high | 126280 | tt10839422 | Sex/Life tv 2021 high | Sex/Life tv 2021 high | compatible |
| 183 | Shadow and Bone S01 | Shadow and Bone | high | Shadow and Bone tv 2021 high | 85720 | tt2403776 | Shadow and Bone tv 2021 high | Shadow and Bone tv 2021 high | compatible |
| 184 | Shadow and Bone S02 | Shadow and Bone | high | Shadow and Bone tv 2021 high | 85720 | tt2403776 | Shadow and Bone tv 2021 high | Shadow and Bone tv 2021 high | compatible |
| 185 | Squid Game S01 | Squid Game | high | Squid Game tv 2021 high | 93405 | tt10919420 | Squid Game tv 2021 high | Squid Game tv 2021 high | compatible |
| 186 | Stranger Things S01 | Stranger Things | high | Stranger Things tv 2016 high | 66732 | tt4574334 | Stranger Things tv 2016 high | Stranger Things tv 2016 high | compatible |
| 187 | Stranger Things S02 | Stranger Things | high | Stranger Things tv 2016 high | 66732 | tt4574334 | Stranger Things tv 2016 high | Stranger Things tv 2016 high | compatible |
| 188 | Stranger Things S03 | Stranger Things | high | Stranger Things tv 2016 high | 66732 | tt4574334 | Stranger Things tv 2016 high | Stranger Things tv 2016 high | compatible |
| 189 | Stranger Things S04 | Stranger Things | high | Stranger Things tv 2016 high | 66732 | tt4574334 | Stranger Things tv 2016 high | Stranger Things tv 2016 high | compatible |
| 190 | Sweet Home S01 | Sweet Home | high | Sweet Home tv 2020 high | 96648 | tt11612120 | Sweet Home tv 2020 high | Sweet Home tv 2020 high | compatible |
| 191 | The Adam Project | The Adam Project | high | The Adam Project movie 2022 high | 696806 | tt2463208 | The Adam Project movie 2022 high | The Adam Project movie 2022 high | compatible |
| 192 | The Bear S01 | The Bear | high | The Bear tv 2022 high | 136315 | tt14452776 | The Bear tv 2022 high | The Bear tv 2022 high | compatible |
| 193 | The Bear S02 | The Bear | high | The Bear tv 2022 high | 136315 | tt14452776 | The Bear tv 2022 high | The Bear tv 2022 high | compatible |
| 194 | The Get Down S01 | The Get Down | high | The Get Down tv 2016 high | 65345 | tt4592410 | The Get Down tv 2016 high | The Get Down tv 2016 high | compatible |
| 195 | The Glory S01 | The Glory | high | The Glory tv 2022 high | 136283 | tt21344706 | The Glory tv 2022 high | The Glory tv 2022 high | compatible |
| 196 | Breaking Bad S01 | Breaking Bad | high | Breaking Bad tv 2008 high | 1396 | tt0903747 | Breaking Bad tv 2008 high | Breaking Bad tv 2008 high | compatible |
| 197 | Breaking Bad S02 | Breaking Bad | high | Breaking Bad tv 2008 high | 1396 | tt0903747 | Breaking Bad tv 2008 high | Breaking Bad tv 2008 high | compatible |
| 198 | Bridgerton S01 | Bridgerton | high | Bridgerton tv 2020 high | 91239 | tt8740790 | Bridgerton tv 2020 high | Bridgerton tv 2020 high | compatible |
| 199 | Children of the Underground S01 | Children of the Underground | high | Children of the Underground tv 2022 high | 206319 | tt20852952 | Children of the Underground tv 2022 high | Children of the Underground tv 2022 high | compatible |
| 200 | Deadwood S01 | Deadwood | high | Deadwood tv 2004 high | 1406 | tt0348914 | Deadwood tv 2004 high | Deadwood tv 2004 high | compatible |
| 201 | Deadwood S02 | Deadwood | high | Deadwood tv 2004 high | 1406 | tt0348914 | Deadwood tv 2004 high | Deadwood tv 2004 high | compatible |
| 202 | Deadwood S03 | Deadwood | high | Deadwood tv 2004 high | 1406 | tt0348914 | Deadwood tv 2004 high | Deadwood tv 2004 high | compatible |
| 203 | Elite S01 | Elite | high | Elite tv 2018 high | 76669 | tt7134908 | Elite tv 2018 high | Elite tv 2018 high | compatible |
| 204 | Elite S02 | Elite | high | Elite tv 2018 high | 76669 | tt7134908 | Elite tv 2018 high | Elite tv 2018 high | compatible |
| 205 | Elite S03 | Elite | high | Elite tv 2018 high | 76669 | tt7134908 | Elite tv 2018 high | Elite tv 2018 high | compatible |
| 206 | Elite S04 | Elite | high | Elite tv 2018 high | 76669 | tt7134908 | Elite tv 2018 high | Elite tv 2018 high | compatible |
| 207 | Elite S05 | Elite | high | Elite tv 2018 high | 76669 | tt7134908 | Elite tv 2018 high | Elite tv 2018 high | compatible |
| 208 | Elite S06 | Elite | high | Elite tv 2018 high | 76669 | tt7134908 | Elite tv 2018 high | Elite tv 2018 high | compatible |
| 209 | I Survived a Crime S01 | I Survived a Crime | high | I Survived a Crime tv 2021 high | 119896 | tt13471702 | I Survived a Crime tv 2021 high | I Survived a Crime tv 2021 high | compatible |
| 210 | Jack Ryan S01 | Jack Ryan | high | Tom Clancy's Jack Ryan tv 2018 high | 73375 | tt5057054 | Tom Clancy's Jack Ryan tv 2018 high | Tom Clancy's Jack Ryan tv 2018 high | compatible |
| 211 | Jack Ryan S02 | Jack Ryan | high | Tom Clancy's Jack Ryan tv 2018 high | 73375 | tt5057054 | Tom Clancy's Jack Ryan tv 2018 high | Tom Clancy's Jack Ryan tv 2018 high | compatible |
| 212 | Jack Ryan S03 | Jack Ryan | high | Tom Clancy's Jack Ryan tv 2018 high | 73375 | tt5057054 | Tom Clancy's Jack Ryan tv 2018 high | Tom Clancy's Jack Ryan tv 2018 high | compatible |
| 213 | Jack Ryan S04 | Jack Ryan | high | Tom Clancy's Jack Ryan tv 2018 high | 73375 | tt5057054 | Tom Clancy's Jack Ryan tv 2018 high | Tom Clancy's Jack Ryan tv 2018 high | compatible |
| 214 | La casa de papel S01 | La casa de papel | high | Money Heist tv 2017 high | 71446 |  | Money Heist tv 2017 high | none no_match no_external_result | tmdb_only |
| 215 | La casa de papel S02 | La casa de papel | high | Money Heist tv 2017 high | 71446 |  | Money Heist tv 2017 high | none no_match no_external_result | tmdb_only |
| 216 | La casa de papel S03 | La casa de papel | high | Money Heist tv 2017 high | 71446 |  | Money Heist tv 2017 high | none no_match no_external_result | tmdb_only |
| 217 | La casa de papel S04 | La casa de papel | high | Money Heist tv 2017 high | 71446 |  | Money Heist tv 2017 high | none no_match no_external_result | tmdb_only |
| 218 | La casa de papel S05 | La casa de papel | high | Money Heist tv 2017 high | 71446 |  | Money Heist tv 2017 high | none no_match no_external_result | tmdb_only |
| 219 | Lost in Space S01 | Lost in Space | high | Lost in Space tv 2018 high | 75758 | tt5232792 | Lost in Space tv 2018 high | Lost in Space tv 2018 high | compatible |
| 220 | Lost in Space S02 | Lost in Space | high | Lost in Space tv 2018 high | 75758 | tt5232792 | Lost in Space tv 2018 high | Lost in Space tv 2018 high | compatible |
| 221 | Lost in Space S03 | Lost in Space | high | Lost in Space tv 2018 high | 75758 | tt5232792 | Lost in Space tv 2018 high | Lost in Space tv 2018 high | compatible |
| 222 | Lucifer S01 | Lucifer | high | Lucifer tv 2016 high | 63174 | tt4052886 | Lucifer tv 2016 high | Lucifer tv 2016 high | compatible |
| 223 | Lucifer S02 | Lucifer | high | Lucifer tv 2016 high | 63174 | tt4052886 | Lucifer tv 2016 high | Lucifer tv 2016 high | compatible |
| 224 | Lucifer S03 | Lucifer | high | Lucifer tv 2016 high | 63174 | tt4052886 | Lucifer tv 2016 high | Lucifer tv 2016 high | compatible |
| 225 | Lucifer S04 | Lucifer | high | Lucifer tv 2016 high | 63174 | tt4052886 | Lucifer tv 2016 high | Lucifer tv 2016 high | compatible |
| 226 | Lucifer S05 | Lucifer | high | Lucifer tv 2016 high | 63174 | tt4052886 | Lucifer tv 2016 high | Lucifer tv 2016 high | compatible |
| 227 | Lucifer S06 | Lucifer | high | Lucifer tv 2016 high | 63174 | tt4052886 | Lucifer tv 2016 high | Lucifer tv 2016 high | compatible |
| 228 | Ozark S01 | Ozark | high | Ozark tv 2017 high | 69740 | tt5071412 | Ozark tv 2017 high | Ozark tv 2017 high | compatible |
| 229 | Ozark S02 | Ozark | high | Ozark tv 2017 high | 69740 | tt5071412 | Ozark tv 2017 high | Ozark tv 2017 high | compatible |
| 230 | Ozark S03 | Ozark | high | Ozark tv 2017 high | 69740 | tt5071412 | Ozark tv 2017 high | Ozark tv 2017 high | compatible |
| 231 | Ozark S04 | Ozark | high | Ozark tv 2017 high | 69740 | tt5071412 | Ozark tv 2017 high | Ozark tv 2017 high | compatible |
| 232 | Platonic S01 | Platonic | high | Platonic tv 2023 high | 112211 | tt13366604 | Platonic tv 2023 high | Platonic tv 2023 high | compatible |
| 233 | Quarterback S01 | Quarterback | high | Quarterback tv 2023 high | 220998 | tt26777035 | Quarterback tv 2023 high | Quarterback tv 2023 high | compatible |
| 234 | Snowpiercer S01 | Snowpiercer | high | Snowpiercer tv 2020 high | 79680 | tt6156584 | Snowpiercer tv 2020 high | Snowpiercer tv 2020 high | compatible |
| 235 | Snowpiercer S02 | Snowpiercer | high | Snowpiercer tv 2020 high | 79680 | tt6156584 | Snowpiercer tv 2020 high | Snowpiercer tv 2020 high | compatible |
| 236 | Snowpiercer S03 | Snowpiercer | high | Snowpiercer tv 2020 high | 79680 | tt6156584 | Snowpiercer tv 2020 high | Snowpiercer tv 2020 high | compatible |
| 237 | Succession S01 | Succession | high | Succession tv 2018 high | 76331 | tt7660850 | Succession tv 2018 high | Succession tv 2018 high | compatible |
| 238 | Succession S02 | Succession | high | Succession tv 2018 high | 76331 | tt7660850 | Succession tv 2018 high | Succession tv 2018 high | compatible |
| 239 | Succession S03 | Succession | high | Succession tv 2018 high | 76331 | tt7660850 | Succession tv 2018 high | Succession tv 2018 high | compatible |
| 240 | Succession S04 | Succession | high | Succession tv 2018 high | 76331 | tt7660850 | Succession tv 2018 high | Succession tv 2018 high | compatible |
| 241 | The Crown S01 | The Crown | high | The Crown tv 2016 high | 65494 | tt4786824 | The Crown tv 2016 high | The Crown tv 2016 high | compatible |
| 242 | The Crown S02 | The Crown | high | The Crown tv 2016 high | 65494 | tt4786824 | The Crown tv 2016 high | The Crown tv 2016 high | compatible |
| 243 | The Crown S03 | The Crown | high | The Crown tv 2016 high | 65494 | tt4786824 | The Crown tv 2016 high | The Crown tv 2016 high | compatible |
| 244 | The Crown S04 | The Crown | high | The Crown tv 2016 high | 65494 | tt4786824 | The Crown tv 2016 high | The Crown tv 2016 high | compatible |
| 245 | The Crown S05 | The Crown | high | The Crown tv 2016 high | 65494 | tt4786824 | The Crown tv 2016 high | The Crown tv 2016 high | compatible |
| 246 | The End of the Fucking World S01 | The End of the Fucking World | high | The End of the F***ing World tv 2017 high | 74577 |  | The End of the F***ing World tv 2017 high | none no_match no_external_result | tmdb_only |
| 247 | The End of the Fucking World S02 | The End of the Fucking World | high | The End of the F***ing World tv 2017 high | 74577 |  | The End of the F***ing World tv 2017 high | none no_match no_external_result | tmdb_only |
| 248 | The Witcher S01 | The Witcher | high | The Witcher tv 2019 high | 71912 | tt5180504 | The Witcher tv 2019 high | The Witcher tv 2019 high | compatible |
| 249 | The Witcher S02 | The Witcher | high | The Witcher tv 2019 high | 71912 | tt5180504 | The Witcher tv 2019 high | The Witcher tv 2019 high | compatible |
| 250 | The Witcher S03 | The Witcher | high | The Witcher tv 2019 high | 71912 | tt5180504 | The Witcher tv 2019 high | The Witcher tv 2019 high | compatible |
| 251 | This Fool S01 | This Fool | high | This Fool tv 2022 high | 202137 | tt14440068 | This Fool tv 2022 high | This Fool tv 2022 high | compatible |
| 252 | Breaking Bad S03 | Breaking Bad | high | Breaking Bad tv 2008 high | 1396 | tt0903747 | Breaking Bad tv 2008 high | Breaking Bad tv 2008 high | compatible |
| 253 | Breaking Bad S04 | Breaking Bad | high | Breaking Bad tv 2008 high | 1396 | tt0903747 | Breaking Bad tv 2008 high | Breaking Bad tv 2008 high | compatible |
| 254 | Breaking Bad S05 | Breaking Bad | high | Breaking Bad tv 2008 high | 1396 | tt0903747 | Breaking Bad tv 2008 high | Breaking Bad tv 2008 high | compatible |
| 255 | Day Shift | Day Shift | high | Day Shift movie 2022 high | 755566 | tt13314558 | Day Shift movie 2022 high | Day Shift movie 2022 high | compatible |
| 256 | Mr. Car and the Knights Templar | Mr. Car and the Knights Templar | high | Mr. Car and the Knights Templar movie 2023 high | 1059638 | tt27876411 | Mr. Car and the Knights Templar movie 2023 high | Mr. Car and the Knights Templar movie 2023 high | compatible |
| 257 | Senior Year | Senior Year | high | Senior Year movie 2022 high | 800937 | tt5315212 | Senior Year movie 2022 high | Senior Year movie 2022 high | compatible |
| 258 | The Empress S01 | The Empress | high | The Empress tv 2022 high | 131488 | tt13720112 | The Empress tv 2022 high | The Empress tv 2022 high | compatible |
| 259 | The Gray Man | The Gray Man | high | The Gray Man movie 2022 high | 725201 | tt1649418 | The Gray Man movie 2022 high | The Gray Man movie 2022 high | compatible |
| 260 | The Kominsky Method S01 | The Kominsky Method | high | The Kominsky Method tv 2018 high | 81290 | tt7255502 | The Kominsky Method tv 2018 high | The Kominsky Method tv 2018 high | compatible |
| 261 | The Kominsky Method S02 | The Kominsky Method | high | The Kominsky Method tv 2018 high | 81290 | tt7255502 | The Kominsky Method tv 2018 high | The Kominsky Method tv 2018 high | compatible |
| 262 | The Kominsky Method S03 | The Kominsky Method | high | The Kominsky Method tv 2018 high | 81290 | tt7255502 | The Kominsky Method tv 2018 high | The Kominsky Method tv 2018 high | compatible |
| 263 | The Larry Sanders Show S01 | The Larry Sanders Show | high | The Larry Sanders Show tv 1992 high | 1915 | tt0103466 | The Larry Sanders Show tv 1992 high | The Larry Sanders Show tv 1992 high | compatible |
| 264 | The Larry Sanders Show S02 | The Larry Sanders Show | high | The Larry Sanders Show tv 1992 high | 1915 | tt0103466 | The Larry Sanders Show tv 1992 high | The Larry Sanders Show tv 1992 high | compatible |
| 265 | The Larry Sanders Show S03 | The Larry Sanders Show | high | The Larry Sanders Show tv 1992 high | 1915 | tt0103466 | The Larry Sanders Show tv 1992 high | The Larry Sanders Show tv 1992 high | compatible |
| 266 | The Larry Sanders Show S04 | The Larry Sanders Show | high | The Larry Sanders Show tv 1992 high | 1915 | tt0103466 | The Larry Sanders Show tv 1992 high | The Larry Sanders Show tv 1992 high | compatible |
| 267 | The Larry Sanders Show S05 | The Larry Sanders Show | high | The Larry Sanders Show tv 1992 high | 1915 | tt0103466 | The Larry Sanders Show tv 1992 high | The Larry Sanders Show tv 1992 high | compatible |
| 268 | The Larry Sanders Show S06 | The Larry Sanders Show | high | The Larry Sanders Show tv 1992 high | 1915 | tt0103466 | The Larry Sanders Show tv 1992 high | The Larry Sanders Show tv 1992 high | compatible |
| 269 | The Man from Toronto | The Man from Toronto | high | The Man from Toronto movie 2022 high | 667739 | tt11671006 | The Man from Toronto movie 2022 high | The Man from Toronto movie 2022 high | compatible |
| 270 | The Marked Heart S01 | The Marked Heart | high | The Marked Heart tv 2022 high | 158916 | tt18974572 | The Marked Heart tv 2022 high | The Marked Heart tv 2022 high | compatible |
| 271 | The Queen's Gambit S01 | The Queen's Gambit | high | The Queen's Gambit tv 2020 high | 87739 | tt10048342 | The Queen's Gambit tv 2020 high | The Queen's Gambit tv 2020 high | compatible |
| 272 | The Sandman S01 | The Sandman | high | The Sandman tv 2022 high | 90802 | tt1751634 | The Sandman tv 2022 high | The Sandman tv 2022 high | compatible |
| 273 | The Sea Beast | The Sea Beast | high | The Sea Beast movie 2022 high | 560057 | tt9288046 | The Sea Beast movie 2022 high | The Sea Beast movie 2022 high | compatible |
| 274 | The Tinder Swindler | The Tinder Swindler | high | The Tinder Swindler movie 2022 high | 923632 | tt14992922 | The Tinder Swindler movie 2022 high | The Tinder Swindler movie 2022 high | compatible |
| 275 | The Umbrella Academy S01 | The Umbrella Academy | high | The Umbrella Academy tv 2019 high | 75006 | tt1312171 | The Umbrella Academy tv 2019 high | The Umbrella Academy tv 2019 high | compatible |
| 276 | The Umbrella Academy S02 | The Umbrella Academy | high | The Umbrella Academy tv 2019 high | 75006 | tt1312171 | The Umbrella Academy tv 2019 high | The Umbrella Academy tv 2019 high | compatible |
| 277 | The Umbrella Academy S03 | The Umbrella Academy | high | The Umbrella Academy tv 2019 high | 75006 | tt1312171 | The Umbrella Academy tv 2019 high | The Umbrella Academy tv 2019 high | compatible |
| 278 | The Watcher S01 | The Watcher | high | The Watcher tv 2022 high | 210232 | tt14852808 | The Watcher tv 2022 high | The Watcher tv 2022 high | compatible |
| 279 | The Wire S01 | The Wire | high | The Wire tv 2002 high | 1438 | tt0306414 | The Wire tv 2002 high | The Wire tv 2002 high | compatible |
| 280 | The Wire S02 | The Wire | high | The Wire tv 2002 high | 1438 | tt0306414 | The Wire tv 2002 high | The Wire tv 2002 high | compatible |
| 281 | The Wire S03 | The Wire | high | The Wire tv 2002 high | 1438 | tt0306414 | The Wire tv 2002 high | The Wire tv 2002 high | compatible |
| 282 | The Wire S04 | The Wire | high | The Wire tv 2002 high | 1438 | tt0306414 | The Wire tv 2002 high | The Wire tv 2002 high | compatible |
| 283 | The Wire S05 | The Wire | high | The Wire tv 2002 high | 1438 | tt0306414 | The Wire tv 2002 high | The Wire tv 2002 high | compatible |
| 284 | This Is Us S01 | This Is Us | medium | This Is Us tv 2020 medium | 318965 | tt5555260 | This Is Us tv 2020 high | This Is Us tv 2016 high | year_delta=4 |
| 285 | This Is Us S02 | This Is Us | medium | This Is Us tv 2020 medium | 318965 | tt5555260 | This Is Us tv 2020 high | This Is Us tv 2016 high | year_delta=4 |
| 286 | This Is Us S03 | This Is Us | medium | This Is Us tv 2020 medium | 318965 | tt5555260 | This Is Us tv 2020 high | This Is Us tv 2016 high | year_delta=4 |
| 287 | This Is Us S04 | This Is Us | medium | This Is Us tv 2020 medium | 318965 | tt5555260 | This Is Us tv 2020 high | This Is Us tv 2016 high | year_delta=4 |
| 288 | This Is Us S05 | This Is Us | medium | This Is Us tv 2020 medium | 318965 | tt5555260 | This Is Us tv 2020 high | This Is Us tv 2016 high | year_delta=4 |
| 289 | This Is Us S06 | This Is Us | medium | This Is Us tv 2020 medium | 318965 | tt5555260 | This Is Us tv 2020 high | This Is Us tv 2016 high | year_delta=4 |
| 290 | True Detective S01 | True Detective | high | True Detective tv 2014 high | 46648 | tt2356777 | True Detective tv 2014 high | True Detective tv 2014 high | compatible |
| 291 | True Detective S02 | True Detective | high | True Detective tv 2014 high | 46648 | tt2356777 | True Detective tv 2014 high | True Detective tv 2014 high | compatible |
| 292 | True Detective S03 | True Detective | high | True Detective tv 2014 high | 46648 | tt2356777 | True Detective tv 2014 high | True Detective tv 2014 high | compatible |
| 293 | Unbelievable S01 | Unbelievable | high | Unbelievable tv 2019 high | 91275 | tt7909970 | Unbelievable tv 2019 high | Unbelievable tv 2019 high | compatible |
| 294 | Vikings S01 | Vikings | high | Vikings tv 2013 high | 44217 | tt2306299 | Vikings tv 2013 high | Vikings tv 2013 high | compatible |
| 295 | Vikings S02 | Vikings | high | Vikings tv 2013 high | 44217 | tt2306299 | Vikings tv 2013 high | Vikings tv 2013 high | compatible |
| 296 | Vikings S03 | Vikings | high | Vikings tv 2013 high | 44217 | tt2306299 | Vikings tv 2013 high | Vikings tv 2013 high | compatible |
| 297 | Vikings S04 | Vikings | high | Vikings tv 2013 high | 44217 | tt2306299 | Vikings tv 2013 high | Vikings tv 2013 high | compatible |
| 298 | Vikings S05 | Vikings | high | Vikings tv 2013 high | 44217 | tt2306299 | Vikings tv 2013 high | Vikings tv 2013 high | compatible |
| 299 | Vikings S06 | Vikings | high | Vikings tv 2013 high | 44217 | tt2306299 | Vikings tv 2013 high | Vikings tv 2013 high | compatible |
| 300 | Vikings Valhalla S01 | Vikings Valhalla | high | Vikings: Valhalla tv 2022 high | 116135 | tt11311302 | Vikings: Valhalla tv 2022 high | Vikings: Valhalla tv 2022 high | compatible |
| 301 | Virgin River S01 | Virgin River | high | Virgin River tv 2019 high | 88324 | tt9077530 | Virgin River tv 2019 high | Virgin River tv 2019 high | compatible |
| 302 | Virgin River S02 | Virgin River | high | Virgin River tv 2019 high | 88324 | tt9077530 | Virgin River tv 2019 high | Virgin River tv 2019 high | compatible |
| 303 | Virgin River S03 | Virgin River | high | Virgin River tv 2019 high | 88324 | tt9077530 | Virgin River tv 2019 high | Virgin River tv 2019 high | compatible |
| 304 | Virgin River S04 | Virgin River | high | Virgin River tv 2019 high | 88324 | tt9077530 | Virgin River tv 2019 high | Virgin River tv 2019 high | compatible |
| 305 | WandaVision S01 | WandaVision | high | WandaVision tv 2021 high | 85271 | tt9140560 | WandaVision tv 2021 high | WandaVision tv 2021 high | compatible |
| 306 | Wednesday S01 | Wednesday | high | Wednesday tv 2022 high | 119051 | tt13443470 | Wednesday tv 2022 high | Wednesday tv 2022 high | compatible |
| 307 | Welcome To Eden S01 | Welcome To Eden | high | Welcome to Eden tv 2022 high | 128010 | tt13457822 | Welcome to Eden tv 2022 high | Welcome to Eden tv 2022 high | compatible |
| 308 | Westworld S01 | Westworld | high | Westworld tv 2016 high | 63247 | tt0475784 | Westworld tv 2016 high | Westworld tv 2016 high | compatible |
| 309 | Westworld S02 | Westworld | high | Westworld tv 2016 high | 63247 | tt0475784 | Westworld tv 2016 high | Westworld tv 2016 high | compatible |
| 310 | Westworld S03 | Westworld | high | Westworld tv 2016 high | 63247 | tt0475784 | Westworld tv 2016 high | Westworld tv 2016 high | compatible |
| 311 | Westworld S04 | Westworld | high | Westworld tv 2016 high | 63247 | tt0475784 | Westworld tv 2016 high | Westworld tv 2016 high | compatible |
| 312 | Who Killed Sara S01 | Who Killed Sara | high | Who Killed Sara? tv 2021 high | 120168 | tt11937816 | Who Killed Sara? tv 2021 high | Who Killed Sara? tv 2021 high | compatible |
| 313 | Who Killed Sara S02 | Who Killed Sara | high | Who Killed Sara? tv 2021 high | 120168 | tt11937816 | Who Killed Sara? tv 2021 high | Who Killed Sara? tv 2021 high | compatible |
| 314 | Who Killed Sara S03 | Who Killed Sara | high | Who Killed Sara? tv 2021 high | 120168 | tt11937816 | Who Killed Sara? tv 2021 high | Who Killed Sara? tv 2021 high | compatible |
| 315 | Wrong Side of the Tracks S01 | Wrong Side of the Tracks | high | Wrong Side of the Tracks tv 2022 high | 128015 | tt13980362 | Wrong Side of the Tracks tv 2022 high | Wrong Side of the Tracks tv 2021 high | compatible |
| 316 | Wrong Side of the Tracks S02 | Wrong Side of the Tracks | high | Wrong Side of the Tracks tv 2022 high | 128015 | tt13980362 | Wrong Side of the Tracks tv 2022 high | Wrong Side of the Tracks tv 2021 high | compatible |
| 317 | You S01 | You | high | You tv 2018 high | 78191 | tt7335184 | You tv 2018 high | You tv 2018 high | compatible |
| 318 | You S02 | You | high | You tv 2018 high | 78191 | tt7335184 | You tv 2018 high | You tv 2018 high | compatible |
| 319 | You S03 | You | high | You tv 2018 high | 78191 | tt7335184 | You tv 2018 high | You tv 2018 high | compatible |
| 320 | You S04 | You | high | You tv 2018 high | 78191 | tt7335184 | You tv 2018 high | You tv 2018 high | compatible |
| 321 | The Night Agent S01 | The Night Agent | high | The Night Agent tv 2023 high | 129552 | tt13918776 | The Night Agent tv 2023 high | The Night Agent tv 2023 high | compatible |
| 322 | The Night Of S01 | The Night Of | high | The Night Of tv 2016 high | 66276 | tt2401256 | The Night Of tv 2016 high | The Night Of tv 2016 high | compatible |
| 323 | The Sopranos S01 | The Sopranos | high | The Sopranos tv 1999 high | 1398 | tt0141842 | The Sopranos tv 1999 high | The Sopranos tv 1999 high | compatible |
| 324 | The Sopranos S02 | The Sopranos | high | The Sopranos tv 1999 high | 1398 | tt0141842 | The Sopranos tv 1999 high | The Sopranos tv 1999 high | compatible |
| 325 | The Sopranos S03 | The Sopranos | high | The Sopranos tv 1999 high | 1398 | tt0141842 | The Sopranos tv 1999 high | The Sopranos tv 1999 high | compatible |
| 326 | The Sopranos S04 | The Sopranos | high | The Sopranos tv 1999 high | 1398 | tt0141842 | The Sopranos tv 1999 high | The Sopranos tv 1999 high | compatible |
| 327 | The Sopranos S05 | The Sopranos | high | The Sopranos tv 1999 high | 1398 | tt0141842 | The Sopranos tv 1999 high | The Sopranos tv 1999 high | compatible |
| 328 | The Sopranos S06 | The Sopranos | high | The Sopranos tv 1999 high | 1398 | tt0141842 | The Sopranos tv 1999 high | The Sopranos tv 1999 high | compatible |
| 329 | The Handmaid's Tale S01 | The Handmaid's Tale | medium | The Handmaid's Tale tv 2017 medium | 69478 | tt15475372 | The Handmaid's Tale tv 2017 high | The Handmaid's Tale tv 2021 high | year_delta=4 |
| 330 | The Handmaid's Tale S02 | The Handmaid's Tale | medium | The Handmaid's Tale tv 2017 medium | 69478 | tt15475372 | The Handmaid's Tale tv 2017 high | The Handmaid's Tale tv 2021 high | year_delta=4 |
| 331 | The Handmaid's Tale S03 | The Handmaid's Tale | medium | The Handmaid's Tale tv 2017 medium | 69478 | tt15475372 | The Handmaid's Tale tv 2017 high | The Handmaid's Tale tv 2021 high | year_delta=4 |
| 332 | The Handmaid's Tale S04 | The Handmaid's Tale | medium | The Handmaid's Tale tv 2017 medium | 69478 | tt15475372 | The Handmaid's Tale tv 2017 high | The Handmaid's Tale tv 2021 high | year_delta=4 |
| 333 | The Handmaid's Tale S05 | The Handmaid's Tale | medium | The Handmaid's Tale tv 2017 medium | 69478 | tt15475372 | The Handmaid's Tale tv 2017 high | The Handmaid's Tale tv 2021 high | year_delta=4 |
| 334 | And Just Like That S01 | And Just Like That | high | And Just Like That… tv 2021 high | 116450 | tt13819960 | And Just Like That… tv 2021 high | And Just Like That... tv 2021 high | compatible |
| 335 | Arnold S01 | Arnold | high | Arnold tv 2023 high | 226135 | tt27713897 | Arnold tv 2023 high | Arnold tv 2023 high | compatible |
| 336 | Black Clover Sword of the Wizard King | Black Clover Sword of the Wizard King | high | Black Clover: Sword of the Wizard King movie 2023 high | 812225 | tt22868844 | Black Clover: Sword of the Wizard King movie 2023 high | Black Clover: Sword of the Wizard King movie 2023 high | compatible |
| 337 | Black Mirror S06 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 338 | Dream | Dream | high | BanG Dream! Girls Band Party!☆PICO tv 2018 high | 80729 | tt1462041 | BanG Dream! Girls Band Party!☆PICO tv 2018 high | Dream House movie 2011 low | type:tv->movie,year_delta=7,title_diff |
| 339 | Fake Profile S01 | Fake Profile | high | Fake Profile tv 2023 high | 227371 | tt14494938 | Fake Profile tv 2023 high | Fake Profile tv 2023 high | compatible |
| 340 | Fast X 2023 | Fast X | high | Fast X movie 2023 high | 385687 | tt5433140 | Fast X movie 2023 high | Fast X movie 2023 high | compatible |
| 341 | Joy Ride | Joy Ride | high | Joy Ride movie 2023 high | 864168 | tt15268244 | Joy Ride movie 2023 high | Joy Ride movie 2023 high | compatible |
| 342 | Kimetsu no Yaiba S04 | Kimetsu no Yaiba | high | Demon Slayer: Kimetsu no Yaiba tv 2019 high | 85937 | tt9335498 | Demon Slayer: Kimetsu no Yaiba tv 2019 high | Demon Slayer: Kimetsu no Yaiba tv 2019 high | compatible |
| 343 | Never Have I Ever S04 | Never Have I Ever | high | Never Have I Ever tv 2020 high | 100883 | tt10062292 | Never Have I Ever tv 2020 high | Never Have I Ever tv 2020 high | compatible |
| 344 | O Rio do DESEJO | O Rio do DESEJO | high | River of Desire movie 2023 high | 764541 |  | River of Desire movie 2023 high | none no_match no_external_result | tmdb_only |
| 345 | Our Planet S02 | Our Planet | medium | Life on Our Planet tv 2023 medium | 213609 | tt9253866 | Life on Our Planet tv 2023 high | Our Planet tv 2019 high | year_delta=4,title_diff |
| 346 | Secret Invasion S01 | Secret Invasion | high | Secret Invasion tv 2023 high | 114472 | tt13157618 | Secret Invasion tv 2023 high | Secret Invasion tv 2023 high | compatible |
| 347 | Spider-Man Across The Spider-Verse 2023 | Spider-Man Across The Spider-Verse | high | Spider-Man: Across the Spider-Verse movie 2023 high | 569094 | tt9362722 | Spider-Man: Across the Spider-Verse movie 2023 high | Spider-Man: Across the Spider-Verse movie 2023 high | compatible |
| 348 | Succession S04 | Succession | high | Succession tv 2018 high | 76331 | tt7660850 | Succession tv 2018 high | Succession tv 2018 high | compatible |
| 349 | Ted Lasso S01 | Ted Lasso | high | Ted Lasso tv 2020 high | 97546 | tt10986410 | Ted Lasso tv 2020 high | Ted Lasso tv 2020 high | compatible |
| 350 | The Bear S02 | The Bear | high | The Bear tv 2022 high | 136315 | tt14452776 | The Bear tv 2022 high | The Bear tv 2022 high | compatible |
| 351 | The Crowded Room S01 | The Crowded Room | high | The Crowded Room tv 2023 high | 123192 | tt14417718 | The Crowded Room tv 2023 high | The Crowded Room tv 2023 high | compatible |
| 352 | The Lincoln Lawyer S01 | The Lincoln Lawyer | high | The Lincoln Lawyer tv 2022 high | 116799 | tt13833978 | The Lincoln Lawyer tv 2022 high | The Lincoln Lawyer tv 2022 high | compatible |
| 353 | The Veil S01 | The Veil | medium | The Veil tv 2021 medium | 127358 | tt21433150 | The Veil tv 2021 high | The Veil tv 2024 high | year_delta=3 |
| 354 | The Witcher S03 | The Witcher | high | The Witcher tv 2019 high | 71912 | tt5180504 | The Witcher tv 2019 high | The Witcher tv 2019 high | compatible |
| 355 | Zombieverse S01 | Zombieverse | high | Zombieverse tv 2023 high | 217945 | tt26770113 | Zombieverse tv 2023 high | Zombieverse tv 2023 high | compatible |
| 356 | And Just Like That S02 | And Just Like That | high | And Just Like That… tv 2021 high | 116450 | tt13819960 | And Just Like That… tv 2021 high | And Just Like That... tv 2021 high | compatible |
| 357 | Bleach Thousand Year Blood War 2023 S02 | Bleach Thousand Year Blood War | medium | Bleach: Thousand-Year Blood War - The Calamity movie 2026 medium | 1669841 | tt14986406 | Bleach: Thousand-Year Blood War - The Calamity movie 2026 medium | Bleach: Thousand-Year Blood War tv 2022 high | type:movie->tv,year_delta=4 |
| 358 | Foundation S02 | Foundation | high | Foundation tv 2021 high | 93740 | tt0804484 | Foundation tv 2021 high | Foundation tv 2021 high | compatible |
| 359 | Good Omens S02 | Good Omens | high | Good Omens tv 2019 high | 71915 | tt1869454 | Good Omens tv 2019 high | Good Omens tv 2019 high | compatible |
| 360 | How To with John Wilson S03 | How To with John Wilson | high | How To with John Wilson tv 2020 high | 110971 | tt10801534 | How To with John Wilson tv 2020 high | How to with John Wilson tv 2020 high | compatible |
| 361 | IDOL The Coup S01 | IDOL The Coup | high | IDOL: The Coup tv 2021 high | 137215 | tt16236014 | IDOL: The Coup tv 2021 high | Idol: The Coup tv 2021 high | compatible |
| 362 | Jujutsu Kaisen S02 | Jujutsu Kaisen | high | JUJUTSU KAISEN tv 2020 high | 95479 | tt12343534 | JUJUTSU KAISEN tv 2020 high | Jujutsu Kaisen tv 2020 high | compatible |
| 363 | King the Land S01 | King the Land | high | King the Land tv 2023 high | 198004 | tt26693803 | King the Land tv 2023 high | King the Land tv 2023 high | compatible |
| 364 | Minx S02 | Minx | high | Minx tv 2022 high | 118303 | tt11947418 | Minx tv 2022 high | Minx tv 2022 high | compatible |
| 365 | Outlander S07 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 366 | The Lincoln Lawyer S02 | The Lincoln Lawyer | high | The Lincoln Lawyer tv 2022 high | 116799 | tt13833978 | The Lincoln Lawyer tv 2022 high | The Lincoln Lawyer tv 2022 high | compatible |
| 367 | Wedding Plan S01 | Wedding Plan | high | Wedding Plan tv 2023 high | 229242 | tt28426949 | Wedding Plan tv 2023 high | Wedding Plan tv 2023 high | compatible |
| 368 | Marry My Dead Body | Marry My Dead Body | high | Marry My Dead Body movie 2023 high | 983883 | tt22742964 | Marry My Dead Body movie 2023 high | Marry My Dead Body movie 2022 high | compatible |
| 369 | heart of stone | heart of stone | high | Heart of Stone movie 2023 high | 724209 | tt13603966 | Heart of Stone movie 2023 high | Heart of Stone movie 2023 high | compatible |
| 370 | Cobweb | Cobweb | high | Cobweb movie 2023 high | 709631 | tt9100018 | Cobweb movie 2023 high | Cobweb movie 2023 high | compatible |
| 371 | How To with John Wilson S03 | How To with John Wilson | high | How To with John Wilson tv 2020 high | 110971 | tt10801534 | How To with John Wilson tv 2020 high | How to with John Wilson tv 2020 high | compatible |
| 372 | And Just Like That S02 | And Just Like That | high | And Just Like That… tv 2021 high | 116450 | tt13819960 | And Just Like That… tv 2021 high | And Just Like That... tv 2021 high | compatible |
| 373 | Bleach Thousand Year Blood War 2023 S02 | Bleach Thousand Year Blood War | medium | Bleach: Thousand-Year Blood War - The Calamity movie 2026 medium | 1669841 | tt14986406 | Bleach: Thousand-Year Blood War - The Calamity movie 2026 medium | Bleach: Thousand-Year Blood War tv 2022 high | type:movie->tv,year_delta=4 |
| 374 | Guns and Gulaabs S01 | Guns and Gulaabs | medium | Guns & Gulaabs tv 2023 medium | 156714 |  | Guns & Gulaabs tv 2023 medium | none no_match no_external_result | tmdb_only |
| 375 | my dad the bounty hunter S02 | my dad the bounty hunter | high | My Dad the Bounty Hunter tv 2023 high | 157221 | tt13433814 | My Dad the Bounty Hunter tv 2023 high | My Dad the Bounty Hunter tv 2023 high | compatible |
| 376 | Jujutsu Kaisen S02 | Jujutsu Kaisen | high | JUJUTSU KAISEN tv 2020 high | 95479 | tt12343534 | JUJUTSU KAISEN tv 2020 high | Jujutsu Kaisen tv 2020 high | compatible |
| 377 | Outlander S07 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 378 | Ramy S01 | Ramy | high | Ramy tv 2019 high | 87382 | tt7649694 | Ramy tv 2019 high | Ramy tv 2019 high | compatible |
| 379 | Ramy S02 | Ramy | high | Ramy tv 2019 high | 87382 | tt7649694 | Ramy tv 2019 high | Ramy tv 2019 high | compatible |
| 380 | The Lincoln Lawyer S02 | The Lincoln Lawyer | high | The Lincoln Lawyer tv 2022 high | 116799 | tt13833978 | The Lincoln Lawyer tv 2022 high | The Lincoln Lawyer tv 2022 high | compatible |
| 381 | The Upshaws S04 | The Upshaws | high | The Upshaws tv 2021 high | 121509 | tt10945036 | The Upshaws tv 2021 high | The Upshaws tv 2021 high | compatible |
| 382 | Wedding Plan S01 | Wedding Plan | high | Wedding Plan tv 2023 high | 229242 | tt28426949 | Wedding Plan tv 2023 high | Wedding Plan tv 2023 high | compatible |
| 383 | Elite S01 | Elite | high | Elite tv 2018 high | 76669 | tt7134908 | Elite tv 2018 high | Elite tv 2018 high | compatible |
| 384 | Who Is Erin Carter S01 | Who Is Erin Carter | high | Who Is Erin Carter? tv 2023 high | 227318 | tt18075020 | Who Is Erin Carter? tv 2023 high | Who Is Erin Carter? tv 2023 high | compatible |
| 385 | Ragnarok S03 | Ragnarok | high | Ragnarok tv 2020 high | 91557 | tt9251798 | Ragnarok tv 2020 high | Ragnarok tv 2020 high | compatible |
| 386 | Squared Love Everlasting | Squared Love Everlasting | high | Squared Love Everlasting movie 2023 high | 1150215 | tt28496500 | Squared Love Everlasting movie 2023 high | Squared Love Everlasting movie 2023 high | compatible |
| 387 | Falcon Lake | Falcon Lake | high | Falcon Lake movie 2022 high | 946127 | tt11448830 | Falcon Lake movie 2022 high | Falcon Lake movie 2022 high | compatible |
| 388 | Fatal Seduction S01 | Fatal Seduction | high | Fatal Seduction tv 2023 high | 227975 | tt27951663 | Fatal Seduction tv 2023 high | Fatal Seduction tv 2023 high | compatible |
| 389 | Spider-Man Across The Spider-Verse | Spider-Man Across The Spider-Verse | high | Spider-Man: Across the Spider-Verse movie 2023 high | 569094 | tt9362722 | Spider-Man: Across the Spider-Verse movie 2023 high | Spider-Man: Across the Spider-Verse movie 2023 high | compatible |
| 390 | The Moon | The Moon | medium | The Moon movie 2023 medium | 753091 | tt1896747 | The Moon movie 2023 high | Fly Me to the Moon movie 2024 high | title_diff |
| 391 | Wanted The Escape of Carlos Ghosn S01 | Wanted The Escape of Carlos Ghosn | high | Wanted: The Escape of Carlos Ghosn tv 2023 high | 231319 | tt15520170 | Wanted: The Escape of Carlos Ghosn tv 2023 high | Wanted: The Escape of Carlos Ghosn tv 2023 high | compatible |
| 392 | Foundation S02 | Foundation | high | Foundation tv 2021 high | 93740 | tt0804484 | Foundation tv 2021 high | Foundation tv 2021 high | compatible |
| 393 | Killer Book Club | Killer Book Club | high | Killer Book Club movie 2023 high | 1010826 | tt18260564 | Killer Book Club movie 2023 high | Killer Book Club movie 2023 high | compatible |
| 394 | NCT 127 The Lost Boys S01 | NCT 127 The Lost Boys | high | NCT 127: The Lost Boys tv 2023 high | 231069 | tt28306746 | NCT 127: The Lost Boys tv 2023 high | NCT 127: The Lost Boys tv 2023 high | compatible |
| 395 | Not Others S01 | Not Others | high | Not Others tv 2023 high | 214891 |  | Not Others tv 2023 high | none no_match no_external_result | tmdb_only |
| 396 | NCT 127 The Lost Boys S01 | NCT 127 The Lost Boys | high | NCT 127: The Lost Boys tv 2023 high | 231069 | tt28306746 | NCT 127: The Lost Boys tv 2023 high | NCT 127: The Lost Boys tv 2023 high | compatible |
| 397 | Choose Love | Choose Love | high | Choose Love movie 2023 high | 956502 | tt19267924 | Choose Love movie 2023 high | Choose Love movie 2023 high | compatible |
| 398 | A Time Called You S01 | A Time Called You | high | A Time Called You tv 2023 high | 196474 | tt21627438 | A Time Called You tv 2023 high | A Time Called You tv 2023 high | compatible |
| 399 | Burning Body S01 | Burning Body | high | Burning Body tv 2023 high | 229962 | tt22073352 | Burning Body tv 2023 high | Burning Body tv 2023 high | compatible |
| 400 | Destined with You | Destined with You | high | Destined with You tv 2023 high | 215001 | tt27974068 | Destined with You tv 2023 high | Destined with You tv 2023 high | compatible |
| 401 | I Am Groot S01 | I Am Groot | high | I Am Groot tv 2022 high | 232125 | tt13623148 | I Am Groot tv 2022 high | I Am Groot tv 2022 high | compatible |
| 402 | I Am Groot S02 | I Am Groot | high | I Am Groot tv 2022 high | 232125 | tt13623148 | I Am Groot tv 2022 high | I Am Groot tv 2022 high | compatible |
| 403 | I Feel You Linger in the Air S01 | I Feel You Linger in the Air | high | I Feel You Linger in the Air tv 2023 high | 212292 | tt15451876 | I Feel You Linger in the Air tv 2023 high | I Feel You Linger in the Air tv 2023 high | compatible |
| 404 | invasion  S01 | invasion | high | Invasion tv 2021 high | 127235 | tt9737326 | Invasion tv 2021 high | Invasion tv 2021 high | compatible |
| 405 | Minx S02 | Minx | high | Minx tv 2022 high | 118303 | tt11947418 | Minx tv 2022 high | Minx tv 2022 high | compatible |
| 406 | Moving S01 | Moving | high | Moving tv 2023 high | 126485 | tt24640580 | Moving tv 2023 high | Moving tv 2023 high | compatible |
| 407 | Physical S03 | Physical | high | Physical tv 2021 high | 119181 | tt11828492 | Physical tv 2021 high | Physical tv 2021 high | compatible |
| 408 | Reporting for Duty S01 | Reporting for Duty | high | Reporting for Duty tv 2023 high | 232644 | tt24578052 | Reporting for Duty tv 2023 high | Reporting for Duty tv 2023 high | compatible |
| 409 | Rosa Peral‘s Tapes S01 | Rosa Peral‘s Tapes | medium | Rosa Peral's Tapes movie 2023 medium | 1167520 |  | Rosa Peral's Tapes movie 2023 medium | none no_match no_external_result | tmdb_only |
| 410 | Scout's Honor The Secret Files of the Boy Scouts of America S01 | Scout's Honor The Secret Files of the Boy Scouts of America | no_match | none no_match api_error=RuntimeError: TraktSearchClient:HTTPError |  |  | no_decision | no_decision | both_no_match |
| 411 | Selling the OC S01 | Selling the OC | high | Selling the OC tv 2022 high | 139566 | tt15907000 | Selling the OC tv 2022 high | Selling the OC tv 2022 high | compatible |
| 412 | Selling the OC S02 | Selling the OC | high | Selling the OC tv 2022 high | 139566 | tt15907000 | Selling the OC tv 2022 high | Selling the OC tv 2022 high | compatible |
| 413 | sitting in bars with cake S01 | sitting in bars with cake | medium | Sitting in Bars with Cake movie 2023 medium | 936952 |  | Sitting in Bars with Cake movie 2023 medium | none no_match no_external_result | tmdb_only |
| 414 | Spy Ops S01 | Spy Ops | high | Spy Ops tv 2023 high | 232401 | tt28637385 | Spy Ops tv 2023 high | Spy Ops tv 2023 high | compatible |
| 415 | Top Boy 2011 S03 | Top Boy | high | Top Boy tv 2011 high | 41889 | tt1830379 | Top Boy tv 2011 high | Top Boy tv 2011 high | compatible |
| 416 | Ahsoka S01 | Ahsoka | high | Ahsoka tv 2023 high | 114461 | tt13622776 | Ahsoka tv 2023 high | Ahsoka tv 2023 high | compatible |
| 417 | Wrestlers S01 | Wrestlers | high | Wrestlers tv 2023 high | 233051 | tt28711468 | Wrestlers tv 2023 high | Wrestlers tv 2023 high | compatible |
| 418 | Kountry Wayne A Womans Prayer S01 | Kountry Wayne A Womans Prayer | medium | Kountry Wayne: A Woman's Prayer movie 2023 medium | 1179875 |  | Kountry Wayne: A Woman's Prayer movie 2023 medium | none no_match no_external_result | tmdb_only |
| 419 | My Sole Desire S01 | My Sole Desire | medium | My Sole Desire movie 2023 medium | 960292 |  | My Sole Desire movie 2023 medium | none no_match no_external_result | tmdb_only |
| 420 | Rapito S01 | Rapito | medium | Kidnapped movie 2023 medium | 801112 |  | Kidnapped movie 2023 medium | none no_match no_external_result | tmdb_only |
| 421 | Wedding Plan S01 | Wedding Plan | high | Wedding Plan tv 2023 high | 229242 | tt28426949 | Wedding Plan tv 2023 high | Wedding Plan tv 2023 high | compatible |
| 422 | Wedding Plan S01 interview | Wedding Plan | high | Wedding Plan tv 2023 high | 229242 | tt28426949 | Wedding Plan tv 2023 high | Wedding Plan tv 2023 high | compatible |
| 423 | ahsoka s01 | ahsoka | high | Ahsoka tv 2023 high | 114461 | tt13622776 | Ahsoka tv 2023 high | Ahsoka tv 2023 high | compatible |
| 424 | All Creatures Great and Small S04 | All Creatures Great and Small | medium | All Creatures Great & Small tv 2020 medium | 108255 | tt3609634 | All Creatures Great & Small tv 2020 high | All Creatures Great and Small tv 2013 high | year_delta=7 |
| 425 | American Horror Story  S12 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 426 | Anatomy Of A Fall S01 | Anatomy Of A Fall | medium | Anatomy of a Fall movie 2023 medium | 915935 |  | Anatomy of a Fall movie 2023 medium | none no_match no_external_result | tmdb_only |
| 427 | Ballerina S01 | Ballerina | medium | Angelina Ballerina tv 2001 medium | 28624 | tt4774562 | Angelina Ballerina tv 2001 high | Nefarious Ballerina tv 2015 high | year_delta=14,title_diff |
| 428 | Behind Your Touch S01 | Behind Your Touch | high | Behind Your Touch tv 2023 high | 210107 | tt26314390 | Behind Your Touch tv 2023 high | Behind Your Touch tv 2023 high | compatible |
| 429 | Bodies S01 | Bodies | high | Bodies tv 2023 high | 233629 | tt18347622 | Bodies tv 2023 high | Bodies tv 2023 high | compatible |
| 430 | Captain Laserhawk A Blood Dragon Remix S01 | Captain Laserhawk A Blood Dragon Remix | high | Captain Laserhawk: A Blood Dragon Remix tv 2023 high | 127372 | tt14837566 | Captain Laserhawk: A Blood Dragon Remix tv 2023 high | Captain Laserhawk: A Blood Dragon Remix tv 2023 high | compatible |
| 431 | Community Squad S01 | Community Squad | high | Community Squad tv 2023 high | 219066 | tt26451138 | Community Squad tv 2023 high | Community Squad tv 2023 high | compatible |
| 432 | Concrete Utopia S01 | Concrete Utopia | medium | Concrete Utopia movie 2023 medium | 729854 |  | Concrete Utopia movie 2023 medium | none no_match no_external_result | tmdb_only |
| 433 | creature s01 | creature | high | Creature tv 2023 high | 214081 | tt17553374 | Creature tv 2023 high | Creature tv 2023 high | compatible |
| 434 | Crypto Boy S01 | Crypto Boy | medium | Crypto Boy movie 2023 medium | 1181538 |  | Crypto Boy movie 2023 medium | none no_match no_external_result | tmdb_only |
| 435 | Disco Inferno S01 | Disco Inferno | medium | Disco Inferno movie 2023 medium | 1191902 |  | Disco Inferno movie 2023 medium | none no_match no_external_result | tmdb_only |
| 436 | Flashback S01 | Flashback | high | Flashback tv 2025 high | 237979 | tt32574953 | Flashback tv 2025 high | Flashback tv 2024 high | compatible |
| 437 | Han River Police S01 | Han River Police | high | Han River Police tv 2023 high | 211020 | tt28090631 | Han River Police tv 2023 high | Han River Police tv 2023 high | compatible |
| 438 | I Feel You Linger in the Air S01 | I Feel You Linger in the Air | high | I Feel You Linger in the Air tv 2023 high | 212292 | tt15451876 | I Feel You Linger in the Air tv 2023 high | I Feel You Linger in the Air tv 2023 high | compatible |
| 439 | Indiana Jones and the Dial of Destiny 5 | Indiana Jones and the Dial of Destiny 5 | high | Indiana Jones and the Dial of Destiny movie 2023 high | 335977 |  | Indiana Jones and the Dial of Destiny movie 2023 high | none no_match no_external_result | tmdb_only |
| 440 | Interrupting Chicken S01 | Interrupting Chicken | high | Interrupting Chicken tv 2022 high | 209131 | tt21942798 | Interrupting Chicken tv 2022 high | Interrupting Chicken tv 2022 high | compatible |
| 441 | invasion s02 | invasion | high | Invasion tv 2021 high | 127235 | tt9737326 | Invasion tv 2021 high | Invasion tv 2021 high | compatible |
| 442 | Kaala Paani S01 | Kaala Paani | high | Kaala Paani tv 2023 high | 235356 | tt19072562 | Kaala Paani tv 2023 high | Kaala Paani tv 2023 high | compatible |
| 443 | Kandasamys The Baby | Kandasamys The Baby | high | Kandasamys: The Baby movie 2023 high | 1181545 | tt27048691 | Kandasamys: The Baby movie 2023 high | Kandasamys: The Baby movie 2023 high | compatible |
| 444 | Loki S02 | Loki | high | Loki tv 2021 high | 84958 | tt9140554 | Loki tv 2021 high | Loki tv 2021 high | compatible |
| 445 | How To with John Wilson S01 | How To with John Wilson | high | How To with John Wilson tv 2020 high | 110971 | tt10801534 | How To with John Wilson tv 2020 high | How to with John Wilson tv 2020 high | compatible |
| 446 | How To with John Wilson S02 | How To with John Wilson | high | How To with John Wilson tv 2020 high | 110971 | tt10801534 | How To with John Wilson tv 2020 high | How to with John Wilson tv 2020 high | compatible |
| 447 | Old Dads | Old Dads | high | Old Dads movie 2023 high | 987917 | tt18394190 | Old Dads movie 2023 high | Old Dads movie 2023 high | compatible |
| 448 | Pantheon S02 | Pantheon | high | Pantheon tv 2022 high | 195339 | tt11680642 | Pantheon tv 2022 high | Pantheon tv 2022 high | compatible |
| 449 | Princess Power S01 | Princess Power | high | Princess Power tv 2023 high | 209708 | tt22013036 | Princess Power tv 2023 high | Princess Power tv 2023 high | compatible |
| 450 | Princess Power S02 | Princess Power | high | Princess Power tv 2023 high | 209708 | tt22013036 | Princess Power tv 2023 high | Princess Power tv 2023 high | compatible |
| 451 | Rookie S01 | Rookie | medium | The Rookie tv 2018 medium | 79744 | tt21299334 | The Rookie tv 2018 high | Old Rookie tv 2022 high | year_delta=4,title_diff |
| 452 | Scavengers Reign S01 | Scavengers Reign | high | Scavengers Reign tv 2023 high | 204154 | tt21056886 | Scavengers Reign tv 2023 high | Scavengers Reign tv 2023 high | compatible |
| 453 | Smugglers S01 | Smugglers | medium | Smugglers movie 2023 medium | 783110 | tt2489782 | Smugglers movie 2023 medium | Smugglers' Cove tv 1963 medium | type:movie->tv,year_delta=60,title_diff |
| 454 | Solar Opposites S01 | Solar Opposites | high | Solar Opposites tv 2020 high | 97645 | tt8910922 | Solar Opposites tv 2020 high | Solar Opposites tv 2020 high | compatible |
| 455 | still up S01 | still up | high | Still Up tv 2023 high | 213337 | tt23033802 | Still Up tv 2023 high | Still Up tv 2023 high | compatible |
| 456 | Strong Girl Nam-soon S01 | Strong Girl Nam-soon | high | Strong Girl Nam-soon tv 2023 high | 203164 | tt29225198 | Strong Girl Nam-soon tv 2023 high | Strong Girl Nam-soon tv 2023 high | compatible |
| 457 | Surviving Paradise S01 | Surviving Paradise | high | Surviving Paradise tv 2023 high | 235441 | tt27849953 | Surviving Paradise tv 2023 high | Surviving Paradise tv 2023 high | compatible |
| 458 | the continental from the world of john wick s01 | the continental from the world of john wick | high | The Continental: From the World of John Wick tv 2023 high | 72710 |  | The Continental: From the World of John Wick tv 2023 high | none no_match no_external_result | tmdb_only |
| 459 | The Devil on Trial S01 | The Devil on Trial | medium | The Devil on Trial movie 2023 medium | 1171989 |  | The Devil on Trial movie 2023 medium | none no_match no_external_result | tmdb_only |
| 460 | The Ghost Station S01 | The Ghost Station | medium | The Ghost Station movie 2023 medium | 844386 |  | The Ghost Station movie 2023 medium | none no_match no_external_result | tmdb_only |
| 461 | The Good Doctor S05 | The Good Doctor | high | The Good Doctor tv 2017 high | 71712 | tt6470478 | The Good Doctor tv 2017 high | The Good Doctor tv 2017 high | compatible |
| 462 | The Good Doctor S06 | The Good Doctor | high | The Good Doctor tv 2017 high | 71712 | tt6470478 | The Good Doctor tv 2017 high | The Good Doctor tv 2017 high | compatible |
| 463 | the morning show S03 | the morning show | high | The Morning Show tv 2019 high | 90282 | tt7203552 | The Morning Show tv 2019 high | The Morning Show tv 2019 high | compatible |
| 464 | The Worst of Evil S01 | The Worst of Evil | high | The Worst of Evil tv 2023 high | 210704 | tt20600022 | The Worst of Evil tv 2023 high | The Worst of Evil tv 2023 high | compatible |
| 465 | Twinkling Watermelon S01 | Twinkling Watermelon | high | Twinkling Watermelon tv 2023 high | 212204 | tt27446493 | Twinkling Watermelon tv 2023 high | Twinkling Watermelon tv 2023 high | compatible |
| 466 | Vjeran Tomic The Spider-Man of Paris S01 | Vjeran Tomic The Spider-Man of Paris | medium | Vjeran Tomic: The Spider-Man of Paris movie 2023 medium | 1183166 |  | Vjeran Tomic: The Spider-Man of Paris movie 2023 medium | none no_match no_external_result | tmdb_only |
| 467 | Get Gotti S01 | Get Gotti | high | Get Gotti tv 2023 high | 236006 | tt29333646 | Get Gotti tv 2023 high | Get Gotti tv 2023 high | compatible |
| 468 | Life on Our Planet S01 | Life on Our Planet | high | Life on Our Planet tv 2023 high | 213609 | tt23181388 | Life on Our Planet tv 2023 high | Life on Our Planet tv 2023 high | compatible |
| 469 | Star Trek Lower Decks S04 | Star Trek Lower Decks | high | Star Trek: Lower Decks tv 2020 high | 85948 | tt9184820 | Star Trek: Lower Decks tv 2020 high | Star Trek: Lower Decks tv 2020 high | compatible |
| 470 | The Killing Vote S01 | The Killing Vote | high | The Killing Vote tv 2023 high | 217088 | tt26471649 | The Killing Vote tv 2023 high | The Killing Vote tv 2023 high | compatible |
| 471 | All Creatures Great and Small S04 | All Creatures Great and Small | medium | All Creatures Great & Small tv 2020 medium | 108255 | tt3609634 | All Creatures Great & Small tv 2020 high | All Creatures Great and Small tv 2013 high | year_delta=7 |
| 472 | All the Light We Cannot See S01 | All the Light We Cannot See | high | All the Light We Cannot See tv 2023 high | 155421 | tt15320362 | All the Light We Cannot See tv 2023 high | All the Light We Cannot See tv 2023 high | compatible |
| 473 | American Horror Story S03 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 474 | American Horror Story S10 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 475 | American Horror Story S11 無英文字幕 | American Horror Story | high | American Horror Story tv 2011 high | 1413 | tt1844624 | American Horror Story tv 2011 high | American Horror Story tv 2011 high | compatible |
| 476 | AND JUST LIKE THAT S02 | AND JUST LIKE THAT | high | And Just Like That… tv 2021 high | 116450 | tt13819960 | And Just Like That… tv 2021 high | And Just Like That... tv 2021 high | compatible |
| 477 | Billions S07 | Billions | high | Billions tv 2016 high | 62852 | tt4270492 | Billions tv 2016 high | Billions tv 2016 high | compatible |
| 478 | Black Mirror S02 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 479 | Black Mirror S04 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 480 | Black Mirror S05 | Black Mirror | high | Black Mirror tv 2011 high | 42009 | tt2085059 | Black Mirror tv 2011 high | Black Mirror tv 2011 high | compatible |
| 481 | Bleach Thousand Year Blood War S01 | Bleach Thousand Year Blood War | medium | Bleach: Thousand-Year Blood War - The Calamity movie 2026 medium | 1669841 | tt14986406 | Bleach: Thousand-Year Blood War - The Calamity movie 2026 medium | Bleach: Thousand-Year Blood War tv 2022 high | type:movie->tv,year_delta=4 |
| 482 | Bleach Thousand Year Blood War S02無英文字幕 | Bleach Thousand Year Blood War | medium | Bleach: Thousand-Year Blood War - The Calamity movie 2026 medium | 1669841 | tt14986406 | Bleach: Thousand-Year Blood War - The Calamity movie 2026 medium | Bleach: Thousand-Year Blood War tv 2022 high | type:movie->tv,year_delta=4 |
| 483 | BoJack Horseman S06 | BoJack Horseman | high | BoJack Horseman tv 2014 high | 61222 | tt3398228 | BoJack Horseman tv 2014 high | BoJack Horseman tv 2014 high | compatible |
| 484 | Castaway Diva S01 | Castaway Diva | high | Castaway Diva tv 2023 high | 216310 | tt28348835 | Castaway Diva tv 2023 high | Castaway Diva tv 2023 high | compatible |
| 485 | Cigarette Girl S01 | Cigarette Girl | high | Cigarette Girl tv 2023 high | 228957 | tt21279114 | Cigarette Girl tv 2023 high | Cigarette Girl tv 2023 high | compatible |
| 486 | Criminal Code S01 | Criminal Code | high | Criminal Code tv 2023 high | 235924 | tt22459586 | Criminal Code tv 2023 high | Criminal Code tv 2023 high | compatible |
| 487 | CSI Vegas S01 | CSI Vegas | high | CSI: Vegas tv 2021 high | 122194 | tt12887536 | CSI: Vegas tv 2021 high | CSI: Vegas tv 2021 high | compatible |
| 488 | Culprits S01 | Culprits | high | Culprits tv 2023 high | 201076 | tt14531774 | Culprits tv 2023 high | Culprits tv 2023 high | compatible |
| 489 | Demon Slayer Kimetsu no Yaiba S01 | Demon Slayer Kimetsu no Yaiba | high | Demon Slayer: Kimetsu no Yaiba tv 2019 high | 85937 | tt9335498 | Demon Slayer: Kimetsu no Yaiba tv 2019 high | Demon Slayer: Kimetsu no Yaiba tv 2019 high | compatible |
| 490 | Fatal Seduction S01 | Fatal Seduction | high | Fatal Seduction tv 2023 high | 227975 | tt27951663 | Fatal Seduction tv 2023 high | Fatal Seduction tv 2023 high | compatible |
| 491 | Fear The Walking Dead S01 | Fear The Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 492 | Fear the Walking Dead S02無英文字幕 | Fear the Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 493 | Fear the Walking Dead S03 | Fear the Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 494 | Fear the Walking Dead S04 | Fear the Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 495 | Fear the Walking Dead S05 | Fear the Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 496 | Fear the Walking Dead S06 | Fear the Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 497 | Fear the Walking Dead S07 | Fear the Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 498 | Fear the Walking Dead S08 | Fear the Walking Dead | high | Fear the Walking Dead tv 2015 high | 62286 | tt3743822 | Fear the Walking Dead tv 2015 high | Fear the Walking Dead tv 2015 high | compatible |
| 499 | fingernails 2023 | fingernails | high | Fingernails movie 2023 high | 790459 | tt13968674 | Fingernails movie 2023 high | Fingernails movie 2023 high | compatible |
| 500 | From S01 | From | high | FROM tv 2022 high | 124364 | tt9813792 | FROM tv 2022 high | From tv 2022 high | compatible |
| 501 | From S02 | From | high | FROM tv 2022 high | 124364 | tt9813792 | FROM tv 2022 high | From tv 2022 high | compatible |
| 502 | GAME OF THRONES S03 | GAME OF THRONES | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 503 | GAME OF THRONES S08 | GAME OF THRONES | high | Game of Thrones tv 2011 high | 1399 | tt0944947 | Game of Thrones tv 2011 high | Game of Thrones tv 2011 high | compatible |
| 504 | Gossip Girl S02 | Gossip Girl | high | Gossip Girl tv 2021 high | 95249 | tt10653784 | Gossip Girl tv 2021 high | Gossip Girl tv 2021 high | compatible |
| 505 | hannah waddingham home for christmas S01 | hannah waddingham home for christmas | medium | Hannah Waddingham: Home for Christmas movie 2023 medium | 1192548 |  | Hannah Waddingham: Home for Christmas movie 2023 medium | none no_match no_external_result | tmdb_only |
| 506 | How to Become a Mob Boss S01 | How to Become a Mob Boss | high | How to Become a Mob Boss tv 2023 high | 237458 | tt29541632 | How to Become a Mob Boss tv 2023 high | How to Become a Mob Boss tv 2023 high | compatible |
| 507 | Invincible 2021 S02 | Invincible | high | INVINCIBLE tv 2021 high | 95557 | tt6741278 | INVINCIBLE tv 2021 high | Invincible tv 2021 high | compatible |
| 508 | Jujutsu Kaisen S01 | Jujutsu Kaisen | high | JUJUTSU KAISEN tv 2020 high | 95479 | tt12343534 | JUJUTSU KAISEN tv 2020 high | Jujutsu Kaisen tv 2020 high | compatible |
| 509 | Julia 2022 S02 | Julia | high | Julia tv 2022 high | 116761 | tt10975574 | Julia tv 2022 high | Julia tv 2022 high | compatible |
| 510 | King the Land S01 | King the Land | high | King the Land tv 2023 high | 198004 | tt26693803 | King the Land tv 2023 high | King the Land tv 2023 high | compatible |
| 511 | Leo 2023 s01 | Leo | high | Léo tv 2018 high | 81840 | tt8004814 | Léo tv 2018 high | Léo tv 2018 high | compatible |
| 512 | Lets Get Divorced S01 | Lets Get Divorced | high | Let's Get Divorced tv 2023 high | 216223 |  | Let's Get Divorced tv 2023 high | none no_match no_external_result | tmdb_only |
| 513 | Locked In 2023 | Locked In | high | Locked In movie 2023 high | 1064024 | tt24870072 | Locked In movie 2023 high | Locked In movie 2023 high | compatible |
| 514 | Lucifer S02 | Lucifer | high | Lucifer tv 2016 high | 63174 | tt4052886 | Lucifer tv 2016 high | Lucifer tv 2016 high | compatible |
| 515 | Lucifer S05 | Lucifer | high | Lucifer tv 2016 high | 63174 | tt4052886 | Lucifer tv 2016 high | Lucifer tv 2016 high | compatible |
| 516 | Lupin S03 | Lupin | high | Lupin tv 2021 high | 96677 | tt2531336 | Lupin tv 2021 high | Lupin tv 2021 high | compatible |
| 517 | Modern Family S07 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 518 | Modern Family S09 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 519 | Modern Family S10 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 520 | Modern Family S11 | Modern Family | high | Modern Family tv 2009 high | 1421 | tt1442437 | Modern Family tv 2009 high | Modern Family tv 2009 high | compatible |
| 521 | My Dad the Bounty Hunter S01 | My Dad the Bounty Hunter | high | My Dad the Bounty Hunter tv 2023 high | 157221 | tt13433814 | My Dad the Bounty Hunter tv 2023 high | My Dad the Bounty Hunter tv 2023 high | compatible |
| 522 | Mysteries of the Faith S01 | Mysteries of the Faith | high | Mysteries of the Faith tv 2023 high | 236505 | tt29416049 | Mysteries of the Faith tv 2023 high | Mysteries of the Faith tv 2023 high | compatible |
| 523 | NCT 127 The Lost Boys S01 | NCT 127 The Lost Boys | high | NCT 127: The Lost Boys tv 2023 high | 231069 | tt28306746 | NCT 127: The Lost Boys tv 2023 high | NCT 127: The Lost Boys tv 2023 high | compatible |
| 524 | Nuovo Olimpo 2023 | Nuovo Olimpo | high | Nuovo Olimpo movie 2023 high | 1044648 | tt18394610 | Nuovo Olimpo movie 2023 high | Nuovo Olimpo movie 2023 high | compatible |
| 525 | Onimusha S01 | Onimusha | high | Onimusha tv 2023 high | 210945 | tt22301234 | Onimusha tv 2023 high | Onimusha tv 2023 high | compatible |
| 526 | Orange Is the New Black S06 | Orange Is the New Black | high | Orange Is the New Black tv 2013 high | 1424 | tt2372162 | Orange Is the New Black tv 2013 high | Orange Is the New Black tv 2013 high | compatible |
| 527 | Orange Is the New Black S07 | Orange Is the New Black | high | Orange Is the New Black tv 2013 high | 1424 | tt2372162 | Orange Is the New Black tv 2013 high | Orange Is the New Black tv 2013 high | compatible |
| 528 | Outlander S01 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 529 | Outlander S02 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 530 | Outlander S03 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 531 | Outlander S04 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 532 | Outlander S05 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 533 | Outlander S06 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 534 | Outlander S07 | Outlander | high | Outlander tv 2014 high | 56570 | tt3006802 | Outlander tv 2014 high | Outlander tv 2014 high | compatible |
| 535 | Scavengers Reign S01 | Scavengers Reign | high | Scavengers Reign tv 2023 high | 204154 | tt21056886 | Scavengers Reign tv 2023 high | Scavengers Reign tv 2023 high | compatible |
| 536 | Ragnarok S01 | Ragnarok | high | Ragnarok tv 2020 high | 91557 | tt9251798 | Ragnarok tv 2020 high | Ragnarok tv 2020 high | compatible |
| 537 | Ragnarok S02 | Ragnarok | high | Ragnarok tv 2020 high | 91557 | tt9251798 | Ragnarok tv 2020 high | Ragnarok tv 2020 high | compatible |
| 538 | Ramy S03 | Ramy | high | Ramy tv 2019 high | 87382 | tt7649694 | Ramy tv 2019 high | Ramy tv 2019 high | compatible |
| 539 | Saw X 2023 | Saw X | high | Saw X movie 2023 high | 951491 | tt21807222 | Saw X movie 2023 high | Saw X movie 2023 high | compatible |
| 540 | Sense8 S02 | Sense8 | high | Sense8 tv 2015 high | 61664 | tt2431438 | Sense8 tv 2015 high | Sense8 tv 2015 high | compatible |
| 541 | Sex Education S04 | Sex Education | high | Sex Education tv 2019 high | 81356 | tt7767422 | Sex Education tv 2019 high | Sex Education tv 2019 high | compatible |
| 542 | Sherlock The Abominable Bride S01 | Sherlock The Abominable Bride | medium | Sherlock: The Abominable Bride movie 2016 medium | 379170 |  | Sherlock: The Abominable Bride movie 2016 medium | none no_match no_external_result | tmdb_only |
| 543 | Sherlock S03 | Sherlock | medium | SHErlock tv 2023 medium | 224755 | tt1475582 | SHErlock tv 2023 high | Sherlock tv 2010 high | year_delta=13 |
| 544 | Sherlock S04 | Sherlock | medium | SHErlock tv 2023 medium | 224755 | tt1475582 | SHErlock tv 2023 high | Sherlock tv 2010 high | year_delta=13 |
| 545 | Silo S01 | Silo | high | Silo tv 2023 high | 125988 | tt14688458 | Silo tv 2023 high | Silo tv 2023 high | compatible |
| 546 | Squid Game The Challenge S01 | Squid Game The Challenge | high | Squid Game: The Challenge tv 2023 high | 204082 | tt28104766 | Squid Game: The Challenge tv 2023 high | Squid Game: The Challenge tv 2023 high | compatible |
| 547 | still up S01 | still up | high | Still Up tv 2023 high | 213337 | tt23033802 | Still Up tv 2023 high | Still Up tv 2023 high | compatible |
| 548 | Strong Girl Nam-soon S01 | Strong Girl Nam-soon | high | Strong Girl Nam-soon tv 2023 high | 203164 | tt29225198 | Strong Girl Nam-soon tv 2023 high | Strong Girl Nam-soon tv 2023 high | compatible |
| 549 | Ted Lasso S02 | Ted Lasso | high | Ted Lasso tv 2020 high | 97546 | tt10986410 | Ted Lasso tv 2020 high | Ted Lasso tv 2020 high | compatible |
| 550 | Ted Lasso S03 | Ted Lasso | high | Ted Lasso tv 2020 high | 97546 | tt10986410 | Ted Lasso tv 2020 high | Ted Lasso tv 2020 high | compatible |
| 551 | The After 2023 | The After | medium | The After tv 2014 medium | 60607 | tt3145422 | The After tv 2014 high | The After movie 2014 high | type:tv->movie |
| 552 | The Big Bang Theory S01 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 553 | The Big Bang Theory S12 | The Big Bang Theory | high | The Big Bang Theory tv 2007 high | 1418 | tt0898266 | The Big Bang Theory tv 2007 high | The Big Bang Theory tv 2007 high | compatible |
| 554 | The Blacklist S03 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 555 | The Blacklist S06 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 556 | The Blacklist S07 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 557 | The Blacklist S08 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 558 | The Blacklist S09 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 559 | The Blacklist S10 | The Blacklist | high | The Blacklist tv 2013 high | 46952 | tt2741602 | The Blacklist tv 2013 high | The Blacklist tv 2013 high | compatible |
| 560 | The Enfield Poltergeist S01 | The Enfield Poltergeist | high | The Enfield Poltergeist tv 2023 high | 235851 | tt21377088 | The Enfield Poltergeist tv 2023 high | The Enfield Poltergeist tv 2023 high | compatible |
| 561 | The Gilded Age S02 | The Gilded Age | high | The Gilded Age tv 2022 high | 81723 | tt4406178 | The Gilded Age tv 2022 high | The Gilded Age tv 2022 high | compatible |
| 562 | THE IDOL S01 | THE IDOL | high | The Idol tv 2023 high | 135251 | tt14954666 | The Idol tv 2023 high | The Idol tv 2023 high | compatible |
| 563 | The Marked Heart S02 | The Marked Heart | high | The Marked Heart tv 2022 high | 158916 | tt18974572 | The Marked Heart tv 2022 high | The Marked Heart tv 2022 high | compatible |
| 564 | The Lincoln Lawye S02 | The Lincoln Lawye | high | The Lincoln Lawyer tv 2022 high | 116799 |  | The Lincoln Lawyer tv 2022 high | none no_match no_external_result | tmdb_only |
| 565 | The Morning Show S03 | The Morning Show | high | The Morning Show tv 2019 high | 90282 | tt7203552 | The Morning Show tv 2019 high | The Morning Show tv 2019 high | compatible |
| 566 | THE SOPRANOS S04 | THE SOPRANOS | high | The Sopranos tv 1999 high | 1398 | tt0141842 | The Sopranos tv 1999 high | The Sopranos tv 1999 high | compatible |
| 567 | This Fool S02 | This Fool | high | This Fool tv 2022 high | 202137 | tt14440068 | This Fool tv 2022 high | This Fool tv 2022 high | compatible |
| 568 | upload S03 | upload | high | Upload tv 2020 high | 86248 | tt7826376 | Upload tv 2020 high | Upload tv 2020 high | compatible |
| 569 | Till Murder Do Us Part Soering vs Haysom S01 | Till Murder Do Us Part Soering vs Haysom | high | Till Murder Do Us Part: Soering vs. Haysom tv 2023 high | 237806 | tt28466971 | Till Murder Do Us Part: Soering vs. Haysom tv 2023 high | Till Murder Do Us Part: Soering vs. Haysom tv 2023 high | compatible |
| 570 | Vigilante S01 | Vigilante | high | Vigilante tv 2023 high | 205082 | tt27458539 | Vigilante tv 2023 high | Vigilante tv 2023 high | compatible |
| 571 | Vikings Valhalla S02 | Vikings Valhalla | high | Vikings: Valhalla tv 2022 high | 116135 | tt11311302 | Vikings: Valhalla tv 2022 high | Vikings: Valhalla tv 2022 high | compatible |
| 572 | Virgin River S05 | Virgin River | high | Virgin River tv 2019 high | 88324 | tt9077530 | Virgin River tv 2019 high | Virgin River tv 2019 high | compatible |
| 573 | Voleuses 2023 | Voleuses | medium | Wingwomen movie 2023 medium | 1010928 | tt1176719 | Wingwomen movie 2023 high | Voleuses movie 1967 high | year_delta=56,title_diff |
| 574 | Wedding Plan S01 | Wedding Plan | high | Wedding Plan tv 2023 high | 229242 | tt28426949 | Wedding Plan tv 2023 high | Wedding Plan tv 2023 high | compatible |
| 575 | Welcome to Eden S02 | Welcome to Eden | high | Welcome to Eden tv 2022 high | 128010 | tt13457822 | Welcome to Eden tv 2022 high | Welcome to Eden tv 2022 high | compatible |
| 576 | A Murder at the End of the World S01 | A Murder at the End of the World | high | A Murder at the End of the World tv 2023 high | 134095 | tt15227418 | A Murder at the End of the World tv 2023 high | A Murder at the End of the World tv 2023 high | compatible |
| 577 | Biosphere S01 | Biosphere | medium | Biosphere movie 2023 medium | 865797 |  | Biosphere movie 2023 medium | none no_match no_external_result | tmdb_only |
| 578 | Birth Rebirth S01 | Birth Rebirth | medium | Birth/Rebirth movie 2023 medium | 1058638 |  | Birth/Rebirth movie 2023 medium | none no_match no_external_result | tmdb_only |
| 579 | Curses S01 | Curses | high | Curses! tv 2023 high | 234800 | tt29180190 | Curses! tv 2023 high | Curses! tv 2023 high | compatible |
| 580 | Family Switch S01 | Family Switch | medium | Family Switch movie 2023 medium | 798021 |  | Family Switch movie 2023 medium | none no_match no_external_result | tmdb_only |
| 581 | Faraway Downs S01 | Faraway Downs | high | Faraway Downs tv 2023 high | 204999 | tt21158320 | Faraway Downs tv 2023 high | Faraway Downs tv 2023 high | compatible |
| 582 | Fargo S05 | Fargo | high | Fargo tv 2014 high | 60622 | tt2802850 | Fargo tv 2014 high | Fargo tv 2014 high | compatible |
| 583 | Fingernails S01 | Fingernails | medium | Fingernails movie 2023 medium | 790459 | tt33669277 | Fingernails movie 2023 medium | There's Light at the Tip of My Fingernails tv 2006 low | type:movie->tv,year_delta=17,title_diff |
| 584 | for all mankind S04 | for all mankind | high | For All Mankind tv 2019 high | 87917 | tt7772588 | For All Mankind tv 2019 high | For All Mankind tv 2019 high | compatible |
| 585 | Its a Wonderful Knife S01 | Its a Wonderful Knife | medium | It's a Wonderful Knife movie 2023 medium | 1113278 |  | It's a Wonderful Knife movie 2023 medium | none no_match no_external_result | tmdb_only |
| 586 | Julia 2022 S02 | Julia | high | Julia tv 2022 high | 116761 | tt10975574 | Julia tv 2022 high | Julia tv 2022 high | compatible |
| 587 | Love Like a K-Drama S01 | Love Like a K-Drama | high | Love Like a K-Drama tv 2023 high | 232433 | tt28628302 | Love Like a K-Drama tv 2023 high | Love Like a K-Drama tv 2023 high | compatible |
| 588 | May December S01 | May December | medium | May December movie 2023 medium | 839369 | tt0096651 | May December movie 2023 medium | May to December tv 1989 medium | type:movie->tv,year_delta=34 |
| 589 | Monarch Legacy of Monsters S01 | Monarch Legacy of Monsters | high | Monarch: Legacy of Monsters tv 2023 high | 202411 | tt17220216 | Monarch: Legacy of Monsters tv 2023 high | Monarch: Legacy of Monsters tv 2023 high | compatible |
| 590 | Nyad S01 | Nyad | medium | NYAD movie 2023 medium | 895549 |  | NYAD movie 2023 medium | none no_match no_external_result | tmdb_only |
| 591 | Obliterated S01 | Obliterated | high | Obliterated tv 2023 high | 94244 | tt11097240 | Obliterated tv 2023 high | Obliterated tv 2023 high | compatible |
| 592 | quiz lady S01 | quiz lady | medium | Quiz Lady movie 2023 medium | 787781 |  | Quiz Lady movie 2023 medium | none no_match no_external_result | tmdb_only |
| 593 | Scott Pilgrim Takes Off S01 | Scott Pilgrim Takes Off | high | Scott Pilgrim Takes Off tv 2023 high | 155292 | tt16969708 | Scott Pilgrim Takes Off tv 2023 high | Scott Pilgrim Takes Off tv 2023 high | compatible |
| 594 | Slow Horses S03 | Slow Horses | high | Slow Horses tv 2022 high | 95480 | tt5875444 | Slow Horses tv 2022 high | Slow Horses tv 2022 high | compatible |
| 595 | Sly S01 | Sly | medium | Sly movie 2023 medium | 1146302 | tt3605850 | Sly movie 2023 medium | You Sly Minx tv 2009 low | type:movie->tv,year_delta=14,title_diff |
| 596 | Squid Game The Challenge S01 | Squid Game The Challenge | high | Squid Game: The Challenge tv 2023 high | 204082 | tt28104766 | Squid Game: The Challenge tv 2023 high | Squid Game: The Challenge tv 2023 high | compatible |
| 597 | Suburraeterna S01 | Suburraeterna | high | Suburræterna tv 2023 high | 235350 | tt28019928 | Suburræterna tv 2023 medium | Suburræterna tv 2023 medium | compatible |
| 598 | The Crown S06 | The Crown | high | The Crown tv 2016 high | 65494 | tt4786824 | The Crown tv 2016 high | The Crown tv 2016 high | compatible |
| 599 | The Gilded Age S02 | The Gilded Age | high | The Gilded Age tv 2022 high | 81723 | tt4406178 | The Gilded Age tv 2022 high | The Gilded Age tv 2022 high | compatible |
| 600 | The Killer S01 | The Killer | high | The Killer tv 1976 high | 109893 | tt11307176 | The Killer tv 1976 high | The Confession Killer tv 2019 low | year_delta=43,title_diff |
| 601 | Vigilante S01 | Vigilante | high | Vigilante tv 2023 high | 205082 | tt27458539 | Vigilante tv 2023 high | Vigilante tv 2023 high | compatible |
| 602 | Wingwomen S01 | Wingwomen | medium | Wingwomen movie 2023 medium | 1010928 |  | Wingwomen movie 2023 medium | none no_match no_external_result | tmdb_only |
| 603 | 3 Body Problem S01 | 3 Body Problem | high | 3 Body Problem tv 2024 high | 108545 | tt13016388 | 3 Body Problem tv 2024 high | 3 Body Problem tv 2024 high | compatible |
| 604 | 9-1-1 S07 | 9-1-1 | high | 9-1-1 tv 2018 high | 75219 | tt7235466 | 9-1-1 tv 2018 high | 9-1-1 tv 2018 high | compatible |
| 605 | A Gentleman in Moscow S01 | A Gentleman in Moscow | high | A Gentleman in Moscow tv 2024 high | 208942 | tt8230448 | A Gentleman in Moscow tv 2024 high | A Gentleman in Moscow tv 2024 high | compatible |
| 606 | A Killer Paradox S01 | A Killer Paradox | high | A Killer Paradox tv 2024 high | 202783 | tt28642796 | A Killer Paradox tv 2024 high | A Killer Paradox tv 2024 high | compatible |
| 607 | Abbott Elementary S03 | Abbott Elementary | high | Abbott Elementary tv 2021 high | 125935 | tt14218830 | Abbott Elementary tv 2021 high | Abbott Elementary tv 2021 high | compatible |
| 608 | About Dry Grasses | About Dry Grasses | high | About Dry Grasses movie 2023 high | 665733 | tt13231544 | About Dry Grasses movie 2023 high | About Dry Grasses movie 2023 high | compatible |
| 609 | Alice and Jack S01 | Alice and Jack | medium | Alice & Jack tv 2024 medium | 232315 |  | Alice & Jack tv 2024 medium | none no_match no_external_result | tmdb_only |
| 610 | Alpha Males S01 | Alpha Males | high | Alpha Males tv 2022 high | 215092 | tt18482892 | Alpha Males tv 2022 high | Alpha Males tv 2022 high | compatible |
| 611 | Alpha Males S02 | Alpha Males | high | Alpha Males tv 2022 high | 215092 | tt18482892 | Alpha Males tv 2022 high | Alpha Males tv 2022 high | compatible |
| 612 | American Dreamer | American Dreamer | high | American Dreamer movie 2022 high | 931461 | tt13884444 | American Dreamer movie 2022 high | American Dreamer movie 2022 high | compatible |
| 613 | American Nightmare S01 | American Nightmare | high | American Nightmare tv 2024 high | 242845 | tt22797582 | American Nightmare tv 2024 high | American Nightmare tv 2024 high | compatible |
| 614 | Animal control S02 | Animal control | high | Animal Control tv 2023 high | 214162 | tt21376524 | Animal Control tv 2023 high | Animal Control tv 2023 high | compatible |
| 615 | Apples Never Fall S01 | Apples Never Fall | high | Apples Never Fall tv 2024 high | 222031 | tt14371926 | Apples Never Fall tv 2024 high | Apples Never Fall tv 2024 high | compatible |
| 616 | Badland Hunters | Badland Hunters | high | Badland Hunters movie 2024 high | 933131 | tt29722855 | Badland Hunters movie 2024 high | Badland Hunters movie 2024 high | compatible |
| 617 | Bastarden | Bastarden | medium | The Promised Land movie 2023 medium | 980026 | tt2013204 | The Promised Land movie 2023 high | Bastarden movie 2009 high | year_delta=14,title_diff |
| 618 | Bleeding Love | Bleeding Love | high | Bleeding Love movie 2024 high | 1000780 | tt15678810 | Bleeding Love movie 2024 high | Bleeding Love movie 2023 high | compatible |
| 619 | Bob Marley One Love | Bob Marley One Love | high | Bob Marley: One Love movie 2024 high | 802219 | tt8521778 | Bob Marley: One Love movie 2024 high | Bob Marley: One Love movie 2024 high | compatible |
| 620 | Captivating the King S01 | Captivating the King | high | Captivating the King tv 2024 high | 233205 | tt29833806 | Captivating the King tv 2024 high | Captivating the King tv 2024 high | compatible |
| 621 | Concrete Utopia | Concrete Utopia | high | Concrete Utopia movie 2023 high | 729854 |  | Concrete Utopia movie 2023 high | none no_match no_external_result | tmdb_only |
| 622 | Constellation S01 | Constellation | high | Constellation tv 2024 high | 197125 | tt19395018 | Constellation tv 2024 high | Constellation tv 2024 high | compatible |
| 623 | Criminal Record S01 | Criminal Record | high | Criminal Record tv 2024 high | 204490 | tt21088136 | Criminal Record tv 2024 high | Criminal Record tv 2024 high | compatible |
| 624 | Cult killer | Cult killer | high | Cult Killer movie 2024 high | 1059345 | tt21151212 | Cult Killer movie 2024 high | Cult Killer movie 2024 high | compatible |
| 625 | Damsel | Damsel | high | Damsel movie 2024 high | 763215 | tt13452446 | Damsel movie 2024 high | Damsel movie 2024 high | compatible |
| 626 | Dario Argento Panico | Dario Argento Panico | high | Dario Argento: Panico movie 2024 high | 1156103 | tt27728888 | Dario Argento: Panico movie 2024 high | Dario Argento: Panico movie 2023 high | compatible |
| 627 | Detective Forst S01 | Detective Forst | high | Detective Forst tv 2024 high | 217522 | tt19723558 | Detective Forst tv 2024 high | Detective Forst tv 2024 high | compatible |
| 628 | Disco Boy | Disco Boy | high | Disco Boy movie 2023 high | 922830 | tt22180518 | Disco Boy movie 2023 high | Disco Boy movie 2023 high | compatible |
| 629 | Drive-Away Dolls | Drive-Away Dolls | high | Drive-Away Dolls movie 2024 high | 957304 | tt19356262 | Drive-Away Dolls movie 2024 high | Drive-Away Dolls movie 2024 high | compatible |
| 630 | Echo S01 | Echo | high | Echo tv 2024 high | 122226 | tt13966962 | Echo tv 2024 high | Echo tv 2023 high | compatible |
| 631 | Dune Part Two | Dune Part Two | high | Dune: Part Two movie 2024 high | 693134 | tt15239678 | Dune: Part Two movie 2024 high | Dune: Part Two movie 2024 high | compatible |
| 632 | Elsbeth S01 | Elsbeth | high | Elsbeth tv 2024 high | 226285 | tt26591110 | Elsbeth tv 2024 high | Elsbeth tv 2024 high | compatible |
| 633 | Expats S01 | Expats | high | Expats tv 2024 high | 95556 | tt8773420 | Expats tv 2024 high | Expats tv 2023 high | compatible |
| 634 | Feud S02 | Feud | high | FEUD tv 2025 high | 252320 | tt33502004 | FEUD tv 2025 high | Feud tv 2025 high | compatible |
| 635 | Fool Me Once S01 | Fool Me Once | high | Fool Me Once tv 2024 high | 220801 | tt5611024 | Fool Me Once tv 2024 high | Fool Me Once tv 2024 high | compatible |
| 636 | Fighter | Fighter | high | Fighter movie 2024 high | 784651 | tt13818368 | Fighter movie 2024 high | Fighter movie 2024 high | compatible |
| 637 | Formula 1 Drive to Survive S03 | Formula 1 Drive to Survive | high | Formula 1: Drive to Survive tv 2019 high | 87083 | tt8289930 | Formula 1: Drive to Survive tv 2019 high | Formula 1: Drive to Survive tv 2019 high | compatible |
| 638 | Formula 1 Drive to Survive S04 | Formula 1 Drive to Survive | high | Formula 1: Drive to Survive tv 2019 high | 87083 | tt8289930 | Formula 1: Drive to Survive tv 2019 high | Formula 1: Drive to Survive tv 2019 high | compatible |
| 639 | Formula 1 Drive to Survive S05 | Formula 1 Drive to Survive | high | Formula 1: Drive to Survive tv 2019 high | 87083 | tt8289930 | Formula 1: Drive to Survive tv 2019 high | Formula 1: Drive to Survive tv 2019 high | compatible |
| 640 | Formula 1 Drive to Survive S06 | Formula 1 Drive to Survive | high | Formula 1: Drive to Survive tv 2019 high | 87083 | tt8289930 | Formula 1: Drive to Survive tv 2019 high | Formula 1: Drive to Survive tv 2019 high | compatible |
| 641 | Frida | Frida | high | Frida movie 2024 high | 1214523 | tt30319555 | Frida movie 2024 high | Frida movie 2024 high | compatible |
| 642 | Ghostbusters Frozen Empire | Ghostbusters Frozen Empire | high | Ghostbusters: Frozen Empire movie 2024 high | 967847 | tt21235248 | Ghostbusters: Frozen Empire movie 2024 high | Ghostbusters: Frozen Empire movie 2024 high | compatible |
| 643 | Girls5eva S03 | Girls5eva | high | Girls5eva tv 2021 high | 100350 | tt11650492 | Girls5eva tv 2021 high | Girls5eva tv 2021 high | compatible |
| 644 | Godzilla X Kong The New Empire | Godzilla X Kong The New Empire | high | Godzilla x Kong: The New Empire movie 2024 high | 823464 | tt14539740 | Godzilla x Kong: The New Empire movie 2024 high | Godzilla x Kong: The New Empire movie 2024 high | compatible |
| 645 | Good Morning Verônica S01 | Good Morning Verônica | high | Good Morning, Verônica tv 2020 high | 110115 | tt12987918 | Good Morning, Verônica tv 2020 high | Good Morning, Verônica tv 2020 high | compatible |
| 646 | Good Morning Verônica S02 | Good Morning Verônica | high | Good Morning, Verônica tv 2020 high | 110115 | tt12987918 | Good Morning, Verônica tv 2020 high | Good Morning, Verônica tv 2020 high | compatible |
| 647 | Good Morning Verônica S03 | Good Morning Verônica | high | Good Morning, Verônica tv 2020 high | 110115 | tt12987918 | Good Morning, Verônica tv 2020 high | Good Morning, Verônica tv 2020 high | compatible |
| 648 | Griselda S01 | Griselda | high | Griselda tv 2024 high | 137893 | tt15837600 | Griselda tv 2024 high | Griselda tv 2024 high | compatible |
| 649 | Hazbin Hotel S01 | Hazbin Hotel | medium | Hazbin Hotel tv 2024 medium | 94954 | tt7216636 | Hazbin Hotel tv 2024 high | Hazbin Hotel tv 2019 high | year_delta=5 |
| 650 | halo S02 | halo | high | Halo tv 2022 high | 52814 | tt2934286 | Halo tv 2022 high | Halo tv 2022 high | compatible |
| 651 | How to Have Sex | How to Have Sex | high | How to Have Sex movie 2023 high | 1075175 | tt22890246 | How to Have Sex movie 2023 high | How to Have Sex movie 2023 high | compatible |
| 652 | Imaginary | Imaginary | high | Imaginary movie 2024 high | 1125311 | tt26658104 | Imaginary movie 2024 high | Imaginary movie 2024 high | compatible |
| 653 | In the Know S01 | In the Know | high | In the Know tv 2024 high | 210684 | tt22177220 | In the Know tv 2024 high | In the Know tv 2024 high | compatible |
| 654 | In The Land Of Saints And Sinners | In The Land Of Saints And Sinners | high | In the Land of Saints and Sinners movie 2023 high | 1027073 | tt15782690 | In the Land of Saints and Sinners movie 2023 high | In the Land of Saints and Sinners movie 2023 high | compatible |
| 655 | Knox Goes Away | Knox Goes Away | high | Knox Goes Away movie 2024 high | 972614 | tt20115766 | Knox Goes Away movie 2024 high | Knox Goes Away movie 2023 high | compatible |
| 656 | Kokomo City | Kokomo City | high | Kokomo City movie 2023 high | 1058678 | tt22528178 | Kokomo City movie 2023 high | Kokomo City movie 2023 high | compatible |
| 657 | Kung Fu Panda | Kung Fu Panda | high | Kung Fu Panda 4 movie 2024 high | 1011985 | tt21692408 | Kung Fu Panda 4 movie 2024 high | Kung Fu Panda 4 movie 2024 high | compatible |
| 658 | Land of Bad | Land of Bad | high | Land of Bad movie 2024 high | 969492 | tt19864802 | Land of Bad movie 2024 high | Land of Bad movie 2024 high | compatible |
| 659 | Life and Beth S02 | Life and Beth | medium | Life & Beth tv 2022 medium | 156812 |  | Life & Beth tv 2022 medium | none no_match no_external_result | tmdb_only |
| 660 | Love Lies Bleeding | Love Lies Bleeding | high | Love Lies Bleeding movie 2024 high | 948549 | tt19637052 | Love Lies Bleeding movie 2024 high | Love Lies Bleeding movie 2024 high | compatible |
| 661 | Luz The Light of the Heart S01 | Luz The Light of the Heart | high | Luz: The Light of the Heart tv 2024 high | 226548 | tt27760092 | Luz: The Light of the Heart tv 2024 high | Luz: The Light of the Heart tv 2024 high | compatible |
| 662 | Madame Web | Madame Web | high | Madame Web movie 2024 high | 634492 | tt11057302 | Madame Web movie 2024 high | Madame Web movie 2024 high | compatible |
| 663 | manhunt S01 | manhunt | high | Manhunt tv 2024 high | 155533 | tt16912512 | Manhunt tv 2024 high | Manhunt tv 2024 high | compatible |
| 664 | Mary and George S01 | Mary and George | medium | Mary & George tv 2024 medium | 212462 | tt2169031 | Mary & George tv 2024 medium | King George and Queen Mary: The Royals Who Rescued the Monarchy tv 2012 low | year_delta=12,title_diff |
| 665 | Mea Culpa | Mea Culpa | high | Mea Culpa movie 2024 high | 1090874 | tt27689459 | Mea Culpa movie 2024 high | Mea Culpa movie 2023 high | compatible |
| 666 | mean girls | mean girls | high | Mean Girls movie 2024 high | 673593 | tt11762114 | Mean Girls movie 2024 high | Mean Girls movie 2024 high | compatible |
| 667 | Memory | Memory | high | Memory movie 2022 high | 818397 | tt11827628 | Memory movie 2022 high | Memory movie 2022 high | compatible |
| 668 | Millers Girl | Millers Girl | high | Miller's Girl movie 2024 high | 1026436 |  | Miller's Girl movie 2024 high | none no_match no_external_result | tmdb_only |
| 669 | Monsieur Spade S01 | Monsieur Spade | high | Monsieur Spade tv 2024 high | 209479 | tt14203572 | Monsieur Spade tv 2024 high | Monsieur Spade tv 2024 high | compatible |
| 670 | Mr and Mrs Smith S01 | Mr and Mrs Smith | medium | Mr. & Mrs. Smith tv 2024 medium | 118642 |  | Mr. & Mrs. Smith tv 2024 medium | none no_match no_external_result | tmdb_only |
| 671 | Next Goal Wins | Next Goal Wins | high | Next Goal Wins movie 2023 high | 621587 | tt10767052 | Next Goal Wins movie 2023 high | Next Goal Wins movie 2023 high | compatible |
| 672 | One Day S01 | One Day | high | One Day tv 2024 high | 240667 | tt16283804 | One Day tv 2024 high | One Day tv 2024 high | compatible |
| 673 | Ordinary Angels | Ordinary Angels | high | Ordinary Angels movie 2024 high | 974036 | tt4996328 | Ordinary Angels movie 2024 high | Ordinary Angels movie 2024 high | compatible |
| 674 | Orion and the Dark | Orion and the Dark | high | Orion and the Dark movie 2024 high | 1139829 | tt28066777 | Orion and the Dark movie 2024 high | Orion and the Dark movie 2024 high | compatible |
| 675 | Palm Royale S01 | Palm Royale | high | Palm Royale tv 2024 high | 157367 | tt8888540 | Palm Royale tv 2024 high | Palm Royale tv 2024 high | compatible |
| 676 | Parish S01 | Parish | high | Parish tv 2024 high | 194741 | tt18552362 | Parish tv 2024 high | Parish tv 2024 high | compatible |
| 677 | Perfect Days | Perfect Days | high | Perfect Days movie 2023 high | 976893 | tt27503384 | Perfect Days movie 2023 high | Perfect Days movie 2023 high | compatible |
| 678 | Peter Five Eight | Peter Five Eight | high | Peter Five Eight movie 2024 high | 974878 | tt15005606 | Peter Five Eight movie 2024 high | Peter Five Eight movie 2024 high | compatible |
| 679 | Race for Glory Audi vs Lancia | Race for Glory Audi vs Lancia | high | Race for Glory: Audi vs. Lancia movie 2024 high | 972433 | tt20112600 | Race for Glory: Audi vs. Lancia movie 2024 high | Race for Glory: Audi vs. Lancia movie 2024 high | compatible |
| 680 | ricky stanicky | ricky stanicky | high | Ricky Stanicky movie 2024 high | 1022690 | tt1660648 | Ricky Stanicky movie 2024 high | Ricky Stanicky movie 2024 high | compatible |
| 681 | Road House | Road House | high | Road House movie 2024 high | 359410 | tt3359350 | Road House movie 2024 high | Road House movie 2024 high | compatible |
| 682 | Avatar The Last Airbender S01 | Avatar The Last Airbender | high | Avatar the Last Airbender tv 2024 high | 82452 | tt9018736 | Avatar the Last Airbender tv 2024 high | Avatar: The Last Airbender tv 2024 high | compatible |
| 683 | the gentlemen S01 | the gentlemen | high | The Gentlemen tv 2024 high | 236235 | tt13210838 | The Gentlemen tv 2024 high | The Gentlemen tv 2024 high | compatible |
| 684 | Sanctuary A Witchs Tale S01 | Sanctuary A Witchs Tale | high | Sanctuary: A Witch's Tale tv 2024 high | 238585 |  | Sanctuary: A Witch's Tale tv 2024 high | none no_match no_external_result | tmdb_only |
| 685 | Shogun S01 | Shogun | high | Shōgun tv 2024 high | 126308 | tt2788316 | Shōgun tv 2024 high | Shogun tv 2024 high | compatible |
| 686 | Society of the Snow | Society of the Snow | high | Society of the Snow movie 2023 high | 906126 | tt16277242 | Society of the Snow movie 2023 high | Society of the Snow movie 2023 high | compatible |
| 687 | Stopmotion | Stopmotion | high | Stopmotion movie 2024 high | 840889 | tt14852624 | Stopmotion movie 2024 high | Stopmotion movie 2023 high | compatible |
| 688 | Suncoast | Suncoast | high | Suncoast movie 2024 high | 1014209 | tt13650742 | Suncoast movie 2024 high | Suncoast movie 2024 high | compatible |
| 689 | Spaceman | Spaceman | high | Spaceman movie 2024 high | 636706 | tt11097384 | Spaceman movie 2024 high | Spaceman movie 2024 high | compatible |
| 690 | Sunderland Til I Die S01 | Sunderland Til I Die | high | Sunderland 'Til I Die tv 2018 high | 84777 | tt8914684 | Sunderland 'Til I Die tv 2018 high | Sunderland 'Til I Die tv 2018 high | compatible |
| 691 | Sunderland Til I Die S02 | Sunderland Til I Die | high | Sunderland 'Til I Die tv 2018 high | 84777 | tt8914684 | Sunderland 'Til I Die tv 2018 high | Sunderland 'Til I Die tv 2018 high | compatible |
| 692 | Sunderland Til I Die S03 | Sunderland Til I Die | high | Sunderland 'Til I Die tv 2018 high | 84777 | tt8914684 | Sunderland 'Til I Die tv 2018 high | Sunderland 'Til I Die tv 2018 high | compatible |
| 693 | Sunrise | Sunrise | high | Sunrise movie 2024 high | 1216784 | tt26742994 | Sunrise movie 2024 high | Sunrise movie 2024 high | compatible |
| 694 | Ted S01 | Ted | high | ted tv 2024 high | 201834 | tt14824792 | ted tv 2024 high | Ted tv 2024 high | compatible |
| 695 | The American Society of Magical Negroes | The American Society of Magical Negroes | high | The American Society of Magical Negroes movie 2024 high | 1039773 | tt30007864 | The American Society of Magical Negroes movie 2024 high | The American Society of Magical Negroes movie 2024 high | compatible |
| 696 | The Beekeeper | The Beekeeper | high | The Beekeeper movie 2024 high | 866398 | tt15314262 | The Beekeeper movie 2024 high | The Beekeeper movie 2024 high | compatible |
| 697 | The Bequeathed S01 | The Bequeathed | high | The Bequeathed tv 2024 high | 212553 | tt28225048 | The Bequeathed tv 2024 high | The Bequeathed tv 2024 high | compatible |
| 698 | The Book Of Clarence | The Book Of Clarence | high | The Book of Clarence movie 2024 high | 976584 | tt22866358 | The Book of Clarence movie 2024 high | The Book of Clarence movie 2023 high | compatible |
| 699 | The Brothers Sun S01 | The Brothers Sun | high | The Brothers Sun tv 2024 high | 227004 | tt17632862 | The Brothers Sun tv 2024 high | The Brothers Sun tv 2024 high | compatible |
| 700 | The Cleaning Lady S03 | The Cleaning Lady | high | The Cleaning Lady tv 2022 high | 125282 | tt11188682 | The Cleaning Lady tv 2022 high | The Cleaning Lady tv 2022 high | compatible |
| 701 | The New Look S01 | The New Look | high | The New Look tv 2024 high | 157368 | tt18177528 | The New Look tv 2024 high | The New Look tv 2024 high | compatible |
| 702 | The Tigers Apprentice | The Tigers Apprentice | high | The Tiger's Apprentice movie 2024 high | 598387 |  | The Tiger's Apprentice movie 2024 high | none no_match no_external_result | tmdb_only |
| 703 | The Tourist S02 | The Tourist | high | The Tourist tv 2022 high | 120909 | tt11847842 | The Tourist tv 2022 high | The Tourist tv 2022 high | compatible |
| 704 | The Walking Dead The Ones Who Live S01 | The Walking Dead The Ones Who Live | high | The Walking Dead: The Ones Who Live tv 2024 high | 206586 | tt9859436 | The Walking Dead: The Ones Who Live tv 2024 high | The Walking Dead: The Ones Who Live tv 2024 high | compatible |
| 705 | This Is Me Now | This Is Me Now | high | This Is Me…Now movie 2024 high | 1217343 | tt30215084 | This Is Me…Now movie 2024 high | This Is Me... Now movie 2024 high | compatible |
| 706 | Through My Window Looking at You | Through My Window Looking at You | high | Through My Window 3: Looking at You movie 2024 high | 1139566 | tt28105944 | Through My Window 3: Looking at You movie 2024 high | Through My Window: Looking at You movie 2024 high | compatible |
| 707 | Tokyo Vice S02 | Tokyo Vice | high | Tokyo Vice tv 2022 high | 90296 | tt2887954 | Tokyo Vice tv 2022 high | Tokyo Vice tv 2022 high | compatible |
| 708 | Tracker S01 | Tracker | high | Tracker tv 2024 high | 211288 | tt13875494 | Tracker tv 2024 high | Tracker tv 2024 high | compatible |
| 709 | True Detective S04 | True Detective | high | True Detective tv 2014 high | 46648 | tt2356777 | True Detective tv 2014 high | True Detective tv 2014 high | compatible |
| 710 | Upgraded | Upgraded | high | Upgraded movie 2024 high | 1014590 | tt21830902 | Upgraded movie 2024 high | Upgraded movie 2024 high | compatible |
| 711 | we were the lucky ones s01 | we were the lucky ones | high | We Were the Lucky Ones tv 2024 high | 200908 | tt9114512 | We Were the Lucky Ones tv 2024 high | We Were the Lucky Ones tv 2024 high | compatible |
| 712 | Which Brings Me to You | Which Brings Me to You | high | Which Brings Me to You movie 2023 high | 975043 | tt3468380 | Which Brings Me to You movie 2023 high | Which Brings Me to You movie 2023 high | compatible |
| 713 | You'll Never Find Me | You'll Never Find Me | high | You'll Never Find Me movie 2024 high | 1117321 | tt22023218 | You'll Never Find Me movie 2024 high | You'll Never Find Me movie 2023 high | compatible |
| 714 | The Regime S01 | The Regime | high | The Regime tv 2024 high | 206829 | tt21375036 | The Regime tv 2024 high | The Regime tv 2024 high | compatible |
| 715 | Love on the Spectrum US S02 | Love on the Spectrum US | high | Love on the Spectrum tv 2022 high | 200731 | tt19037550 | Love on the Spectrum tv 2022 high | Love on the Spectrum U.S. tv 2022 high | compatible |
| 716 | All Creatures Great and Small  S04 | All Creatures Great and Small | medium | All Creatures Great & Small tv 2020 medium | 108255 | tt3609634 | All Creatures Great & Small tv 2020 high | All Creatures Great and Small tv 2013 high | year_delta=7 |
| 717 | Barbie | Barbie | high | Barbie movie 2023 high | 346698 | tt1517268 | Barbie movie 2023 high | Barbie movie 2023 high | compatible |
| 718 | Dragons of Wonderhatch S01 | Dragons of Wonderhatch | high | Dragons of Wonderhatch tv 2023 high | 236520 | tt23874192 | Dragons of Wonderhatch tv 2023 high | Dragons of Wonderhatch tv 2023 high | compatible |
| 719 | High Tides S01 | High Tides | high | High Tides tv 2023 high | 203616 | tt21093806 | High Tides tv 2023 high | High Tides tv 2023 high | compatible |
| 720 | Julia S02 | Julia | high | Julia tv 2022 high | 116761 | tt10975574 | Julia tv 2022 high | Julia tv 2022 high | compatible |
| 721 | La La Land | La La Land | high | La La Land movie 2016 high | 313369 | tt3783958 | La La Land movie 2016 high | La La Land movie 2016 high | compatible |
| 722 | Loudermilk S01 | Loudermilk | high | Loudermilk tv 2017 high | 73200 | tt5957766 | Loudermilk tv 2017 high | Loudermilk tv 2017 high | compatible |
| 723 | Loudermilk S02 | Loudermilk | high | Loudermilk tv 2017 high | 73200 | tt5957766 | Loudermilk tv 2017 high | Loudermilk tv 2017 high | compatible |
| 724 | Loudermilk S03 | Loudermilk | high | Loudermilk tv 2017 high | 73200 | tt5957766 | Loudermilk tv 2017 high | Loudermilk tv 2017 high | compatible |
| 725 | 9-1-1 S07 | 9-1-1 | high | 9-1-1 tv 2018 high | 75219 | tt7235466 | 9-1-1 tv 2018 high | 9-1-1 tv 2018 high | compatible |
| 726 | A Gentleman in Moscow S01 | A Gentleman in Moscow | high | A Gentleman in Moscow tv 2024 high | 208942 | tt8230448 | A Gentleman in Moscow tv 2024 high | A Gentleman in Moscow tv 2024 high | compatible |
| 727 | Abbott Elementary S03 | Abbott Elementary | high | Abbott Elementary tv 2021 high | 125935 | tt14218830 | Abbott Elementary tv 2021 high | Abbott Elementary tv 2021 high | compatible |
| 728 | Animal Control S02 | Animal Control | high | Animal Control tv 2023 high | 214162 | tt21376524 | Animal Control tv 2023 high | Animal Control tv 2023 high | compatible |
| 729 | Argylle | Argylle | high | Argylle movie 2024 high | 848538 | tt15009428 | Argylle movie 2024 high | Argylle movie 2024 high | compatible |
| 730 | Arthur the King | Arthur the King | high | Arthur the King movie 2024 high | 618588 | tt10720352 | Arthur the King movie 2024 high | Arthur the King movie 2024 high | compatible |
| 731 | Bandidos S01 | Bandidos | high | Bandidos tv 2024 high | 241269 | tt11262142 | Bandidos tv 2024 high | Bandidos tv 2024 high | compatible |
| 732 | Chicken Nugget S01 | Chicken Nugget | high | Chicken Nugget tv 2024 high | 206686 | tt28642797 | Chicken Nugget tv 2024 high | Chicken Nugget tv 2024 high | compatible |
| 733 | Cult Killer | Cult Killer | high | Cult Killer movie 2024 high | 1059345 | tt21151212 | Cult Killer movie 2024 high | Cult Killer movie 2024 high | compatible |
| 734 | Curb Your Enthusiasm S12 | Curb Your Enthusiasm | high | Curb Your Enthusiasm tv 2000 high | 4546 | tt0264235 | Curb Your Enthusiasm tv 2000 high | Curb Your Enthusiasm tv 2000 high | compatible |
| 735 | Echo S01 | Echo | high | Echo tv 2024 high | 122226 | tt13966962 | Echo tv 2024 high | Echo tv 2023 high | compatible |
| 736 | Eileen | Eileen | high | Eileen movie 2023 high | 664341 | tt5198890 | Eileen movie 2023 high | Eileen movie 2023 high | compatible |
| 737 | Elsbeth S01 | Elsbeth | high | Elsbeth tv 2024 high | 226285 | tt26591110 | Elsbeth tv 2024 high | Elsbeth tv 2024 high | compatible |
| 738 | Godzilla vs Kong 2021 | Godzilla vs Kong | high | Godzilla vs. Kong movie 2021 high | 399566 | tt5034838 | Godzilla vs. Kong movie 2021 high | Godzilla vs. Kong movie 2021 high | compatible |
| 739 | Godzilla x Kong The New Empire | Godzilla x Kong The New Empire | high | Godzilla x Kong: The New Empire movie 2024 high | 823464 | tt14539740 | Godzilla x Kong: The New Empire movie 2024 high | Godzilla x Kong: The New Empire movie 2024 high | compatible |
| 740 | Io Capitano | Io Capitano | high | Io Capitano movie 2023 high | 937746 | tt14225838 | Io Capitano movie 2023 high | Io Capitano movie 2023 high | compatible |
| 741 | Jukkakukan no Satsujin | Jukkakukan no Satsujin | high | Jukkakukan no satsujin tv 2024 high |  | tt31898580 | none no_match no_external_result | Jukkakukan no satsujin tv 2024 high | omdb_only |
| 742 | Julia S02 | Julia | high | Julia tv 2022 high | 116761 | tt10975574 | Julia tv 2022 high | Julia tv 2022 high | compatible |
| 743 | Late Night with the Devil | Late Night with the Devil | high | Late Night with the Devil movie 2024 high | 938614 | tt14966898 | Late Night with the Devil movie 2024 high | Late Night with the Devil movie 2023 high | compatible |
| 744 | law and order organized crime S04 | law and order organized crime | high | Law & Order: Organized Crime tv 2021 high | 106158 |  | Law & Order: Organized Crime tv 2021 high | none no_match no_external_result | tmdb_only |
| 745 | manhunt S01 | manhunt | high | Manhunt tv 2024 high | 155533 | tt16912512 | Manhunt tv 2024 high | Manhunt tv 2024 high | compatible |
| 746 | Marry My Husband S01 | Marry My Husband | high | Marry My Husband tv 2024 high | 221851 | tt26628595 | Marry My Husband tv 2024 high | Marry My Husband tv 2024 high | compatible |
| 747 | NCIS Hawaii S03 | NCIS Hawaii | high | NCIS: Hawaiʻi tv 2021 high | 124271 |  | NCIS: Hawaiʻi tv 2021 high | none no_match no_external_result | tmdb_only |
| 748 | Haikyuu!! S01 | Haikyuu!! | high | Haikyu!! tv 2014 high | 60863 | tt11474434 | Haikyu!! tv 2014 high | Blind Wave: Haikyuu Reaction tv 2019 low | year_delta=5,title_diff |
| 749 | Haikyuu!! S02 | Haikyuu!! | high | Haikyu!! tv 2014 high | 60863 | tt11474434 | Haikyu!! tv 2014 high | Blind Wave: Haikyuu Reaction tv 2019 low | year_delta=5,title_diff |
| 750 | Haikyuu!! S03 | Haikyuu!! | high | Haikyu!! tv 2014 high | 60863 | tt11474434 | Haikyu!! tv 2014 high | Blind Wave: Haikyuu Reaction tv 2019 low | year_delta=5,title_diff |
| 751 | Haikyuu!! S04 | Haikyuu!! | high | Haikyu!! tv 2014 high | 60863 | tt11474434 | Haikyu!! tv 2014 high | Blind Wave: Haikyuu Reaction tv 2019 low | year_delta=5,title_diff |
| 752 | loot S02 | loot | high | Loot tv 2022 high | 197449 | tt14271498 | Loot tv 2022 high | Loot tv 2022 high | compatible |
| 753 | Oppenheimer | Oppenheimer | high | Oppenheimer movie 2023 high | 872585 | tt15398776 | Oppenheimer movie 2023 high | Oppenheimer movie 2023 high | compatible |
| 754 | Palm Royale S01 | Palm Royale | high | Palm Royale tv 2024 high | 157367 | tt8888540 | Palm Royale tv 2024 high | Palm Royale tv 2024 high | compatible |
| 755 | Parish S01 | Parish | high | Parish tv 2024 high | 194741 | tt18552362 | Parish tv 2024 high | Parish tv 2024 high | compatible |
| 756 | Plata quemada | Plata quemada | high | Burnt Money movie 2000 high | 27092 |  | Burnt Money movie 2000 high | none no_match no_external_result | tmdb_only |
| 757 | Problemista | Problemista | high | Problemista movie 2024 high | 852247 | tt15078804 | Problemista movie 2024 high | Problemista movie 2023 high | compatible |
| 758 | Race for Glory Audi vs Lancia | Race for Glory Audi vs Lancia | high | Race for Glory: Audi vs. Lancia movie 2024 high | 972433 | tt20112600 | Race for Glory: Audi vs. Lancia movie 2024 high | Race for Glory: Audi vs. Lancia movie 2024 high | compatible |
| 759 | Resident Alien S03 | Resident Alien | high | Resident Alien tv 2021 high | 96580 | tt8690918 | Resident Alien tv 2021 high | Resident Alien tv 2021 high | compatible |
| 760 | Reacher S02 | Reacher | high | Reacher tv 2022 high | 108978 | tt9288030 | Reacher tv 2022 high | Reacher tv 2022 high | compatible |
| 761 | Senorita 89 S01 | Senorita 89 | high | Señorita 89 tv 2022 high | 155645 | tt16589104 | Señorita 89 tv 2022 high | Señorita 89 tv 2022 high | compatible |
| 762 | Taylor Swift The Eras Tour 2023 | Taylor Swift The Eras Tour | high | TAYLOR SWIFT \| THE ERAS TOUR movie 2023 high | 1160164 | tt28814949 | TAYLOR SWIFT \| THE ERAS TOUR movie 2023 high | Taylor Swift: The Eras Tour movie 2023 high | compatible |
| 763 | The Believers S01 | The Believers | high | The Believers tv 2024 high | 244571 | tt31158584 | The Believers tv 2024 high | The Believers tv 2024 high | compatible |
| 764 | The Cleaning Lady  S03 | The Cleaning Lady | high | The Cleaning Lady tv 2022 high | 125282 | tt11188682 | The Cleaning Lady tv 2022 high | The Cleaning Lady tv 2022 high | compatible |
| 765 | The Completely Made-Up Adventures of Dick Turpin S01 | The Completely Made-Up Adventures of Dick Turpin | high | The Completely Made-Up Adventures of Dick Turpin tv 2024 high | 197459 | tt19516036 | The Completely Made-Up Adventures of Dick Turpin tv 2024 high | The Completely Made-Up Adventures of Dick Turpin tv 2024 high | compatible |
| 766 | the dynasty new england patriots S01 | the dynasty new england patriots | high | The Dynasty: New England Patriots tv 2024 high | 239748 | tt18257378 | The Dynasty: New England Patriots tv 2024 high | The Dynasty: New England Patriots tv 2024 high | compatible |
| 767 | The Gilded Age S02 | The Gilded Age | high | The Gilded Age tv 2022 high | 81723 | tt4406178 | The Gilded Age tv 2022 high | The Gilded Age tv 2022 high | compatible |
| 768 | Shogun S01 | Shogun | high | Shōgun tv 2024 high | 126308 | tt2788316 | Shōgun tv 2024 high | Shogun tv 2024 high | compatible |
| 769 | The Story of Parks Marriage Contract S01 | The Story of Parks Marriage Contract | high | The Story of Park's Marriage Contract tv 2023 high | 220076 |  | The Story of Park's Marriage Contract tv 2023 high | none no_match no_external_result | tmdb_only |
| 770 | The Vienna Boys' Choir Silk Songs Along The Road And Time | The Vienna Boys' Choir Silk Songs Along The Road And Time | no_match | none no_match api_error=RuntimeError: TraktSearchClient:HTTPError |  |  | no_decision | no_decision | both_no_match |
| 771 | the walking dead the ones who live S01 | the walking dead the ones who live | high | The Walking Dead: The Ones Who Live tv 2024 high | 206586 | tt9859436 | The Walking Dead: The Ones Who Live tv 2024 high | The Walking Dead: The Ones Who Live tv 2024 high | compatible |
| 772 | the zone of interest | the zone of interest | high | The Zone of Interest movie 2023 high | 467244 | tt7160372 | The Zone of Interest movie 2023 high | The Zone of Interest movie 2023 high | compatible |
| 773 | Tracker S01 | Tracker | high | Tracker tv 2024 high | 211288 | tt13875494 | Tracker tv 2024 high | Tracker tv 2024 high | compatible |
| 774 | Vigil S02 | Vigil | high | Vigil tv 2021 high | 126167 | tt11846996 | Vigil tv 2021 high | Vigil tv 2021 high | compatible |
| 775 | we were the lucky ones S01 | we were the lucky ones | high | We Were the Lucky Ones tv 2024 high | 200908 | tt9114512 | We Were the Lucky Ones tv 2024 high | We Were the Lucky Ones tv 2024 high | compatible |
| 776 | Welcome to Samdal-ri S01 | Welcome to Samdal-ri | high | Welcome to Samdal-ri tv 2023 high | 219651 |  | Welcome to Samdal-ri tv 2023 high | none no_match no_external_result | tmdb_only |
| 777 | What If S02 | What If | high | What If...? tv 2021 high | 91363 | tt10168312 | What If...? tv 2021 high | What If...? tv 2021 high | compatible |
| 778 | World War II From the Frontlines S01 | World War II From the Frontlines | high | World War II: From the Frontlines tv 2023 high | 233237 | tt28756878 | World War II: From the Frontlines tv 2023 high | World War II: From the Frontlines tv 2023 high | compatible |
| 779 | Moon in The Day S01 | Moon in The Day | high | Moon in the Day tv 2023 high | 230924 | tt29224935 | Moon in the Day tv 2023 high | Moon in the Day tv 2023 high | compatible |
| 780 | The Matchmakers S01 | The Matchmakers | high | The Matchmakers tv 2023 high | 230024 | tt29274743 | The Matchmakers tv 2023 high | The Matchmakers tv 2023 high | compatible |
| 781 | Agatha All Along S01 | Agatha All Along | high | Agatha All Along tv 2024 high | 138501 | tt15571732 | Agatha All Along tv 2024 high | Agatha All Along tv 2024 high | compatible |
| 782 | Deceitful Love S01 | Deceitful Love | high | Deceitful Love tv 2024 high | 265156 | tt27031470 | Deceitful Love tv 2024 high | Deceitful Love tv 2024 high | compatible |
| 783 | Disclaimer S01 | Disclaimer | high | Disclaimer tv 2024 high | 147050 | tt16294384 | Disclaimer tv 2024 high | Disclaimer tv 2024 high | compatible |
| 784 | Envious S01 | Envious | high | Envious tv 2024 high | 261615 | tt29494111 | Envious tv 2024 high | Envious tv 2024 high | compatible |
| 785 | From S03 | From | high | FROM tv 2022 high | 124364 | tt9813792 | FROM tv 2022 high | From tv 2022 high | compatible |
| 786 | Hacks S03 | Hacks | high | Hacks tv 2021 high | 124101 | tt11815682 | Hacks tv 2021 high | Hacks tv 2021 high | compatible |
| 787 | House of the Dragon S01 | House of the Dragon | high | House of the Dragon tv 2022 high | 94997 | tt11198330 | House of the Dragon tv 2022 high | House of the Dragon tv 2022 high | compatible |
| 788 | House of the Dragon S02 | House of the Dragon | high | House of the Dragon tv 2022 high | 94997 | tt11198330 | House of the Dragon tv 2022 high | House of the Dragon tv 2022 high | compatible |
| 789 | Loki S02 | Loki | high | Loki tv 2021 high | 84958 | tt9140554 | Loki tv 2021 high | Loki tv 2021 high | compatible |
| 790 | Loki S01 | Loki | high | Loki tv 2021 high | 84958 | tt9140554 | Loki tv 2021 high | Loki tv 2021 high | compatible |
| 791 | Love Is Blind S01 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 792 | Love Is Blind S02 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 793 | Love Is Blind S03 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 794 | Love Is Blind S04 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 795 | Love Is Blind S05 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 796 | Love Is Blind S06 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 797 | Love Is Blind S07 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 798 | Margarita S01 | Margarita | medium | Margarita tv 2007 medium | 12711 | tt33145195 | Margarita tv 2007 high | Margarita tv 2024 high | year_delta=17 |
| 799 | Outer Banks S01 | Outer Banks | high | Outer Banks tv 2020 high | 100757 | tt10293938 | Outer Banks tv 2020 high | Outer Banks tv 2020 high | compatible |
| 800 | Outer Banks S02 | Outer Banks | high | Outer Banks tv 2020 high | 100757 | tt10293938 | Outer Banks tv 2020 high | Outer Banks tv 2020 high | compatible |
| 801 | Outer Banks S04 | Outer Banks | high | Outer Banks tv 2020 high | 100757 | tt10293938 | Outer Banks tv 2020 high | Outer Banks tv 2020 high | compatible |
| 802 | Outer Banks S03 | Outer Banks | high | Outer Banks tv 2020 high | 100757 | tt10293938 | Outer Banks tv 2020 high | Outer Banks tv 2020 high | compatible |
| 803 | Rivals S01 | Rivals | high | Rivals tv 2024 high | 208921 | tt21906238 | Rivals tv 2024 high | Rivals tv 2024 high | compatible |
| 804 | Shrinking S01 | Shrinking | high | Shrinking tv 2023 high | 136311 | tt15677150 | Shrinking tv 2023 high | Shrinking tv 2023 high | compatible |
| 805 | Shrinking S02 | Shrinking | high | Shrinking tv 2023 high | 136311 | tt15677150 | Shrinking tv 2023 high | Shrinking tv 2023 high | compatible |
| 806 | Slow Horses S01 | Slow Horses | high | Slow Horses tv 2022 high | 95480 | tt5875444 | Slow Horses tv 2022 high | Slow Horses tv 2022 high | compatible |
| 807 | Slow Horses S02 | Slow Horses | high | Slow Horses tv 2022 high | 95480 | tt5875444 | Slow Horses tv 2022 high | Slow Horses tv 2022 high | compatible |
| 808 | Slow Horses S03 | Slow Horses | high | Slow Horses tv 2022 high | 95480 | tt5875444 | Slow Horses tv 2022 high | Slow Horses tv 2022 high | compatible |
| 809 | Slow Horses S04 | Slow Horses | high | Slow Horses tv 2022 high | 95480 | tt5875444 | Slow Horses tv 2022 high | Slow Horses tv 2022 high | compatible |
| 810 | The Lincoln Lawyer S02 | The Lincoln Lawyer | high | The Lincoln Lawyer tv 2022 high | 116799 | tt13833978 | The Lincoln Lawyer tv 2022 high | The Lincoln Lawyer tv 2022 high | compatible |
| 811 | The Lincoln Lawyer S03 | The Lincoln Lawyer | high | The Lincoln Lawyer tv 2022 high | 116799 | tt13833978 | The Lincoln Lawyer tv 2022 high | The Lincoln Lawyer tv 2022 high | compatible |
| 812 | The Lincoln Lawyer S01 | The Lincoln Lawyer | high | The Lincoln Lawyer tv 2022 high | 116799 | tt13833978 | The Lincoln Lawyer tv 2022 high | The Lincoln Lawyer tv 2022 high | compatible |
| 813 | The Lord of the Rings-The Rings of Power S01 | The Lord of the Rings-The Rings of Power | high | The Lord of the Rings: The Rings of Power tv 2022 high | 84773 | tt7631058 | The Lord of the Rings: The Rings of Power tv 2022 high | The Lord of the Rings: The Rings of Power tv 2022 high | compatible |
| 814 | The Lord of the Rings-The Rings of Power S02 | The Lord of the Rings-The Rings of Power | high | The Lord of the Rings: The Rings of Power tv 2022 high | 84773 | tt7631058 | The Lord of the Rings: The Rings of Power tv 2022 high | The Lord of the Rings: The Rings of Power tv 2022 high | compatible |
| 815 | The Penguin S01 | The Penguin | high | The Penguin tv 2024 high | 194764 | tt15435876 | The Penguin tv 2024 high | The Penguin tv 2024 high | compatible |
| 816 | Wheres Wanda S01 | Wheres Wanda | high | Where's Wanda? tv 2024 high | 234310 |  | Where's Wanda? tv 2024 high | none no_match no_external_result | tmdb_only |
| 817 | The World Is Not Enough S01 | The World Is Not Enough | medium | The World Is Not Enough movie 1999 medium | 36643 | tt10888604 | The World Is Not Enough movie 1999 medium | The World Is Not Enough: The Making of a Blockbuster tv 1999 low | type:movie->tv,title_diff |
| 818 | Margarita S01 | Margarita | medium | Margarita tv 2007 medium | 12711 | tt33145195 | Margarita tv 2007 high | Margarita tv 2024 high | year_delta=17 |
| 819 | Cross S01 | Cross | high | Cross tv 2024 high | 213306 | tt11794812 | Cross tv 2024 high | Cross tv 2024 high | compatible |
| 820 | Dawn of the Planet of the Apes S01 | Dawn of the Planet of the Apes | medium | Dawn of the Planet of the Apes movie 2014 medium | 119450 |  | Dawn of the Planet of the Apes movie 2014 medium | none no_match no_external_result | tmdb_only |
| 821 | Deceitful Love S01 | Deceitful Love | high | Deceitful Love tv 2024 high | 265156 | tt27031470 | Deceitful Love tv 2024 high | Deceitful Love tv 2024 high | compatible |
| 822 | Elsbeth S02 | Elsbeth | high | Elsbeth tv 2024 high | 226285 | tt26591110 | Elsbeth tv 2024 high | Elsbeth tv 2024 high | compatible |
| 823 | Disclaimer S01 | Disclaimer | high | Disclaimer tv 2024 high | 147050 | tt16294384 | Disclaimer tv 2024 high | Disclaimer tv 2024 high | compatible |
| 824 | Agatha All Along S01 | Agatha All Along | high | Agatha All Along tv 2024 high | 138501 | tt15571732 | Agatha All Along tv 2024 high | Agatha All Along tv 2024 high | compatible |
| 825 | Envious S01 | Envious | high | Envious tv 2024 high | 261615 | tt29494111 | Envious tv 2024 high | Envious tv 2024 high | compatible |
| 826 | Hacks S03 | Hacks | high | Hacks tv 2021 high | 124101 | tt11815682 | Hacks tv 2021 high | Hacks tv 2021 high | compatible |
| 827 | Kita no kuni kara '98 jidai S01 | Kita no kuni kara '98 jidai | medium | Kita no kuni kara '98 Jidai Part 2 movie 1998 medium | 993913 |  | Kita no kuni kara '98 Jidai Part 2 movie 1998 medium | none no_match no_external_result | tmdb_only |
| 828 | Love Is Blind S07百度网盘 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 829 | The Sex Lives of College Girls S03 | The Sex Lives of College Girls | high | The Sex Lives of College Girls tv 2021 high | 134373 | tt11212276 | The Sex Lives of College Girls tv 2021 high | The Sex Lives of College Girls tv 2021 high | compatible |
| 830 | When the Phone Rings S01 | When the Phone Rings | high | When the Phone Rings tv 2024 high | 253905 | tt33503491 | When the Phone Rings tv 2024 high | When the Phone Rings tv 2024 high | compatible |
| 831 | Fight Night The Million Dollar Heist S01 | Fight Night The Million Dollar Heist | high | Fight Night: The Million Dollar Heist tv 2024 high | 241485 | tt30428188 | Fight Night: The Million Dollar Heist tv 2024 high | Fight Night: The Million Dollar Heist tv 2024 high | compatible |
| 832 | Kingdom Of The Planet Of The Apes | Kingdom Of The Planet Of The Apes | high | Kingdom of the Planet of the Apes movie 2024 high | 653346 | tt11389872 | Kingdom of the Planet of the Apes movie 2024 high | Kingdom of the Planet of the Apes movie 2024 high | compatible |
| 833 | Rise of the Planet of the Apes | Rise of the Planet of the Apes | high | Rise of the Planet of the Apes movie 2011 high | 61791 | tt1318514 | Rise of the Planet of the Apes movie 2011 high | Rise of the Planet of the Apes movie 2011 high | compatible |
| 834 | War for the Planet of the Apes | War for the Planet of the Apes | high | War for the Planet of the Apes movie 2017 high | 281338 | tt3450958 | War for the Planet of the Apes movie 2017 high | War for the Planet of the Apes movie 2017 high | compatible |
| 835 | Outer Banks S04 | Outer Banks | high | Outer Banks tv 2020 high | 100757 | tt10293938 | Outer Banks tv 2020 high | Outer Banks tv 2020 high | compatible |
| 836 | Love Is Blind S03 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 837 | Love Is Blind S06 | Love Is Blind | high | Love Is Blind tv 2020 high | 99353 | tt11704040 | Love Is Blind tv 2020 high | Love Is Blind tv 2020 high | compatible |
| 838 | Shrinking S02 | Shrinking | high | Shrinking tv 2023 high | 136311 | tt15677150 | Shrinking tv 2023 high | Shrinking tv 2023 high | compatible |
| 839 | The Penguin S01 | The Penguin | high | The Penguin tv 2024 high | 194764 | tt15435876 | The Penguin tv 2024 high | The Penguin tv 2024 high | compatible |
| 840 | Wheres Wanda S01 | Wheres Wanda | high | Where's Wanda? tv 2024 high | 234310 |  | Where's Wanda? tv 2024 high | none no_match no_external_result | tmdb_only |
| 841 | 3 Body Problem S01 | 3 Body Problem | high | 3 Body Problem tv 2024 high | 108545 | tt13016388 | 3 Body Problem tv 2024 high | 3 Body Problem tv 2024 high | compatible |
| 842 | Black Doves S01 | Black Doves | high | Black Doves tv 2024 high | 225385 | tt27995113 | Black Doves tv 2024 high | Black Doves tv 2024 high | compatible |
| 843 | Elsbeth S01 | Elsbeth | high | Elsbeth tv 2024 high | 226285 | tt26591110 | Elsbeth tv 2024 high | Elsbeth tv 2024 high | compatible |
| 844 | Elsbeth S02 | Elsbeth | high | Elsbeth tv 2024 high | 226285 | tt26591110 | Elsbeth tv 2024 high | Elsbeth tv 2024 high | compatible |
| 845 | Lioness S02 | Lioness | high | Lioness tv 2023 high | 113962 | tt13111078 | Lioness tv 2023 high | Lioness tv 2023 high | compatible |
| 846 | Silo S02 | Silo | high | Silo tv 2023 high | 125988 | tt14688458 | Silo tv 2023 high | Silo tv 2023 high | compatible |
| 847 | Special Ops Lioness S01 | Special Ops Lioness | low | Lioness tv 2023 low | 113962 |  | Lioness tv 2023 low | none no_match no_external_result | tmdb_only |
| 848 | Star Wars Skeleton Crew S01 | Star Wars Skeleton Crew | high | Star Wars: Skeleton Crew tv 2024 high | 202879 |  | Star Wars: Skeleton Crew tv 2024 high | none no_match no_external_result | tmdb_only |
| 849 | The Agency S01 | The Agency | medium | The Agency tv 2020 medium | 108179 | tt6101574 | The Agency tv 2020 high | The Agency tv 2016 high | year_delta=4 |
| 850 | The Day Of The Jackal S01 | The Day Of The Jackal | high | The Day of the Jackal tv 2024 high | 222766 | tt24053860 | The Day of the Jackal tv 2024 high | The Day of the Jackal tv 2024 high | compatible |
| 851 | Yellowstone S01 | Yellowstone | high | Yellowstone tv 2018 high | 73586 | tt4236770 | Yellowstone tv 2018 high | Yellowstone tv 2018 high | compatible |
| 852 | Yellowstone S02 | Yellowstone | high | Yellowstone tv 2018 high | 73586 | tt4236770 | Yellowstone tv 2018 high | Yellowstone tv 2018 high | compatible |
| 853 | Yellowstone S04 | Yellowstone | high | Yellowstone tv 2018 high | 73586 | tt4236770 | Yellowstone tv 2018 high | Yellowstone tv 2018 high | compatible |
| 854 | Yellowstone S05 | Yellowstone | high | Yellowstone tv 2018 high | 73586 | tt4236770 | Yellowstone tv 2018 high | Yellowstone tv 2018 high | compatible |
| 855 | The Madness S01 | The Madness | high | The Madness tv 2024 high | 220056 | tt26676489 | The Madness tv 2024 high | The Madness tv 2024 high | compatible |

## 4. 人工复核建议

- 优先抽样复核 high 匹配，目标准确率 >= 95%。
- 对 low / no_match 样本补充年份、类型或外部 ID 后再重跑。
- 本报告不代表自动写入 canonical_items 的授权。
