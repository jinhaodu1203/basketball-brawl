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

# Version 2.0.1 - Basic Dribble System
新增效果：
- 持球时篮球在手与地面之间循环运球
- 移动运球速度比原地运球更快
- 移动时篮球会略微向前摆动
- 跳跃时自动收球
- 蓄力投篮时自动收球
- 不改变原有 AI 投篮、抢断、篮筐碰撞和得分逻辑