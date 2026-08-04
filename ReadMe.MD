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