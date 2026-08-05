# Version 0.4 — Character Ability Framework

## 新角色

- **DJH**：专属技能 `Lightning Dash`
- **Gorilla**：专属技能 `Ground Slam`
- **Ninja**：专属技能 `Shadow Jump`（空中二段跳）

## 操作

| 操作 | 玩家1 | 玩家2 |
|---|---|---|
| 移动 | A / D | ← / → |
| 跳跃 | W | ↑ |
| 投篮/捡球 | Space | Enter |
| 抢断 | S | ↓ |
| 角色技能 | Left Shift | Right Ctrl |

## 资源目录

```text
assets/characters/djh/
assets/characters/gorilla/
assets/characters/ninja/
```

每个角色目录未来可以加入：`portrait.png`、`idle.png`、`run.png`、`jump.png`、`shoot.png`。

更新了作者的名字和加入了作者的角色。



# Version 0.5 - Arena System

新增：
- 场景选择界面：Sunset Street / Neon Gym / Moon Rooftop
- 每张地图拥有独立地面、篮筐、三分线、出生位置配置
- 删除压扁椭圆三分线，改为适合2D侧视角的清晰地板边界线
- 支持自定义背景图：`assets/arenas/<arena_id>/background.png`

背景图片建议尺寸：960 × 540，PNG。


# Version 0.6 - 更改投篮机制

借鉴 NBA2K Sports, 增加了投篮属性和投篮条
玩家1长按 Space 蓄力，松开投篮
玩家2长按 Enter 蓄力，松开投篮
角色头顶显示投篮力度条
绿色区域是完美出手区
松开太早会投短
松开太晚会投长
蓄力到满会自动出手
AI 投篮逻辑保持正常

# 三个角色的投篮差异：

DJH：完美区最宽，最稳定
Gorilla：蓄力较慢，完美区最窄
Ninja：蓄力最快，完美区中等


# Version 0.7 - Rim and Backboard Physics

新增内容：

- 篮球可以撞击篮板并反弹
- 篮球可以撞击篮圈左右两端并产生真实方向反弹
- 得分判定改为“篮球从上向下穿过篮圈”，高速投篮也不容易漏判
- 场景加入简单篮网视觉
- 原有角色技能、场景选择和蓄力投篮全部保留

建议测试：

1. 故意投短，观察前框反弹。
2. 故意投长，观察后框或篮板反弹。
3. 完美出手应能正常穿框得分。
4. 三张地图都测试一次。

# Version 0.8 - Game Feel and Pause System

新增内容：

- 抢断成功显示 `STEAL!`，并加入闪光、粒子、顿帧和震屏
- Gorilla 震地命中显示 `SLAM!`
- DJH Dash 现在可以撞飞对手并打掉篮球，命中显示 `DASH HIT!`
- Ninja 二段跳加入 `SHADOW JUMP!` 提示和粒子
- 完美投篮显示 `PERFECT!`
- 进球、撞框和撞板加入不同强度的画面反馈
- ESC 不再直接退出；比赛中按 ESC 打开暂停菜单
- 暂停菜单支持继续、重开、返回主菜单和退出游戏

暂停菜单操作：

- ESC / P：继续
- R：重新开始本场比赛
- M：返回主菜单
- Q：退出游戏


# Version 0.8.1 - Reduced Visual Feedback

- 大幅降低屏幕抖动幅度和持续时间。
- 只在角色释放技能和进球时显示特效与轻微震屏。
- 篮球撞篮圈、撞篮板和普通抢断不再触发特效或震屏。
- DJH Dash、Gorilla Ground Slam、Ninja Shadow Jump 与进球保留简化反馈。


# Version 2.0.2 - Block System

新增盖帽系统：

- 不增加新按键，防守者跳起后会自动尝试封盖。
- 手部命中飞行中的对手投篮时显示 `BLOCK!`。
- 被盖的球会改变轨迹并进入 loose 状态，可以继续争抢。
- 高速投篮使用上一帧到当前帧的轨迹线段判定，减少穿模漏判。
- AI 会根据篮球位置自动追球并起跳封盖。
- 每位角色记录本场盖帽次数（`player.blocks`），为后续数据面板预留。

# V2.0.2.2 Hotfix
- 修复篮球无人持有时抢断逻辑访问 None 导致崩溃。
- 被盖、投篮飞行和篮板争抢期间均可安全运行。

# V2.0.3 - Rebound System
新增：
- 投篮撞到篮圈或篮板后进入可抢篮板状态
- 球员起跳并接近篮球时自动抓下篮板
- 两人同时争抢时按手部距离与卡位位置决定归属
- AI 会主动移动、起跳并争抢篮板
- 成功篮板显示 REBOUND! 与轻微画面反馈
- 每名球员记录 rebounds 数据
- 盖帽后的篮球同样可以直接争抢篮板

操作：
- P1：W 起跳抢板
- P2：方向键上 起跳抢板
- 无需新增按键