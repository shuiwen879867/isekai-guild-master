# 对战器状态 API

对战器网站默认监听 `http://服务器地址:6680`。以下接口只读、返回 UTF-8 JSON，并允许跨域读取；不需要登录，也不会返回密码、手牌、房间聊天、恢复令牌或观战私密信息。

## 接口

| 请求 | 用途 |
| --- | --- |
| `GET /api/health` | 最小存活检查，在线时返回 `{"online": true}` |
| `GET /api/status` | 服务器总览、在线连接数、进行中房间和玩家名 |
| `GET /api/rooms` | 仅返回正在游玩的房间数组 |
| `GET /api/rooms/{房间ID}` | 返回一个正在游玩的房间详情；不存在时为 HTTP 404 |

`/api/status` 的主要字段：

- `online`：服务器是否在线。
- `connected_people`：当前连接到对战器的总人数，包含仍在房间列表中的用户和观战者。
- `active_room_count`：正在游玩的房间数。
- `active_player_count`：这些房间内的席位总数。
- `active_online_player_count`：这些席位中当前已连接的数量。
- `players`：正在游玩的玩家名列表。
- `rooms`：房间详情数组。

房间详情包含 `id`、`name`、`started_at`、`duration_seconds`、`phase`、`round`、`season`、`civilization`、`miasma`、`map_type`、当前玩家数、总席位数以及玩家列表。退出的席位仍保留在房间详情里并标记 `withdrawn: true`，但不计入 `player_count`、`active_player_count` 和顶层 `players`。玩家项只含席位、名字、看板娘、连接/闭店/退出状态。

示例：

```json
{
  "online": true,
  "connected_people": 5,
  "active_room_count": 1,
  "active_player_count": 3,
  "active_online_player_count": 2,
  "players": ["Alice", "Bob", "Carol"],
  "rooms": [
    {
      "id": "12AB34CD",
      "name": "周末局",
      "duration_seconds": 742,
      "civilization": 7,
      "miasma": 12,
      "players": [{"id": 0, "name": "Alice", "connected": true, "closed": false}]
    }
  ]
}
```

机器人应把 HTTP 连接失败、超时或非 2xx 响应视为服务器离线，并避免高频轮询；建议间隔至少 10 秒。

## 回放与胜率 API（6767）

默认回放地址为 `http://服务器地址:6767`，新增以下只读接口。查询列表和当日摘要只含玩家名、角色、开局行动顺位、声望与获胜者，不含手牌或私密选项。

| 请求 | 用途 |
| --- | --- |
| `GET /api/replays?date=today` | 当日对局摘要；`date=all` 或 `YYYY-MM-DD` 可切换范围 |
| `GET /api/daily?date=today&limit=4&offset=0` | 机器人分页预览，包含总场次、已结束、进行中、中断与 `matches` |
| `GET /api/statistics?date=all&players=5` | 开局行动顺位和角色胜率；省略 `players` 汇总所有多人局 |

日期使用北京时间，按对局的开局时间归档。`limit` 为 1–100，`offset` 不小于零。参数不合法时返回 HTTP 400。`preview.players` 包含 `id/name/hero/hero_name/variant/seat/position/score/rank/winner`；`preview.winner_names` 列出最终获胜者。`seat` 只标识预览中的 P1–P5，胜率只统计开局行动顺位 `position`。

`/api/statistics` 返回 `matches`、`positions`、`heroes` 和统计口径 `note`。每行包含 `games/wins/win_rate`，胜率为百分数；角色行额外包含 `hero/name/variant`。仅已结束多人局且有原引擎获胜者时纳入统计；平局并列第一各记一胜，黑白角色版本分别计算。单人、进行中、中断局不进入胜率；旧回放无需迁移或重录。

独立 AstrBot 插件见 `integrations/astrbot_plugin_guild_replay/`，与 GuanpengNet 无依赖。`/g查询` 以图片展示当日预览与获胜者，`/g胜率` 以图片展示行动顺位和角色胜率。默认连接6767，插件设置中可修改地址。
