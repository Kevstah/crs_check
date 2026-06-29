
```
curl ^"https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c^&poolCode=hhad,had^" ^
  -H ^"accept: application/json, text/javascript, */*; q=0.01^" ^
  -H ^"accept-language: zh-CN,zh;q=0.9,ja;q=0.8,zh-TW;q=0.7,en;q=0.6,sq;q=0.5,am;q=0.4^" ^
  -H ^"origin: https://m.sporttery.cn^" ^
  -H ^"priority: u=1, i^" ^
  -H ^"referer: https://m.sporttery.cn/^" ^
  -H ^"sec-ch-ua: ^\^"Google Chrome^\^";v=^\^"149^\^", ^\^"Chromium^\^";v=^\^"149^\^", ^\^"Not)A;Brand^\^";v=^\^"24^\^"^" ^
  -H ^"sec-ch-ua-mobile: ?0^" ^
  -H ^"sec-ch-ua-platform: ^\^"Windows^\^"^" ^
  -H ^"sec-fetch-dest: empty^" ^
  -H ^"sec-fetch-mode: cors^" ^
  -H ^"sec-fetch-site: same-site^" ^
  -H ^"user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36^"
  
  ```


```
curl ^"https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c^&poolCode=crs^" ^
  -H ^"accept: application/json, text/javascript, */*; q=0.01^" ^
  -H ^"accept-language: zh-CN,zh;q=0.9,ja;q=0.8,zh-TW;q=0.7,en;q=0.6,sq;q=0.5,am;q=0.4^" ^
  -H ^"origin: https://m.sporttery.cn^" ^
  -H ^"priority: u=1, i^" ^
  -H ^"referer: https://m.sporttery.cn/^" ^
  -H ^"sec-ch-ua: ^\^"Google Chrome^\^";v=^\^"149^\^", ^\^"Chromium^\^";v=^\^"149^\^", ^\^"Not)A;Brand^\^";v=^\^"24^\^"^" ^
  -H ^"sec-ch-ua-mobile: ?0^" ^
  -H ^"sec-ch-ua-platform: ^\^"Windows^\^"^" ^
  -H ^"sec-fetch-dest: empty^" ^
  -H ^"sec-fetch-mode: cors^" ^
  -H ^"sec-fetch-site: same-site^" ^
  -H ^"user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36^"
```

页面修改:
- "来源文件: data_record\gamble_record_2026-06-28 21-09-24.json | 生成时间: 2026-06-28 21:14:26"不要
- 标题改成 比分赔率
- 下面呈现方式改成: 一个框内一个比分黑色粗体 下面有灰色稍小一点的赔率 然后每个比赛下面可以有好几行 一行有若干个框(一行最多5个) 状态不要 updateDate updateTime都不要 然后允许用户进行框的点击, 点击逻辑如下:
    每场比赛下每个比分自带一个计数器 默认为0 且0不显示 点一次则计数器加一
    - 计数器为0 不显示数字 框白色背景
    - 计数器为1 显示数字1框框右上角 框红色背景
    - 计数器为2 显示数字2框框右上角 框黄色背景
    - 计数器为3 显示数字3框框右上角 框绿色背景
    每场比赛下最多总计数器加起来为3 当某次用户点击>3的时候自动重置**当前**比赛的全部点击为0(不必提示)

# 数据注入
连接数据库的方式可以在`visual_test.ipynb`看到, 我在public下有一个名为crs_match_info的表格, 现在需要你对这个表格进行数据注入, 当前注入的方式就是用 `gamble_record_2026-06-28 21-09-24.json`这个文件内的数据, 之后我会有新的json来给你. 下面详细讲一下注入的细节:
    - match_id和json中保持一致, 每个match_id下应该有且仅有一行数据, 每次注入数据前进行检查, match_id是否已经在表格中存在, 如果存在则跳过
    - create_at数据库会自动分配
    - match_time:             
                "matchDate"拼 "matchTime",比如"2026-06-29 03:00:00" 特别注意, 这是一个text格式列
    - match_category: 用 "leagueAbbName"的值
    - match_home_team: "homeTeamAbbName",
    - match_away_team: "awayTeamAbbName"的值,
    - crs: "crs"的值, 这列是个json格式的, 注入字典之前进行几步处理: "goalLine", "goalLineValue", "updateDate", "updateTime", 结尾有"f"这几个键不要, 其他的键做一下处理成可读的比分说明, 请你参见`generate_crs_html.py`里面的解析方式