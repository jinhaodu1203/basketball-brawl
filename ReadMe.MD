# Basketball Brawl

一款使用 **Python + Pygame** 开发的 2D 街机篮球对战游戏。

玩家可以选择不同角色，在多张球场地图中完成投篮、扣篮、抢断、篮板和盖帽，并使用每个角色独有的技能进行对战。

> Current Build: **V3.0 Development Build**

---

## 游戏模式

点击主菜单中的 **开始游戏 / Play** 后，可以选择：

### 1. AI

单人对战 AI。

流程：

```text
选择玩家角色
→ 选择 AI 角色
→ 选择 AI 难度
→ 选择球场
→ 开始比赛
```

AI 难度：

- EZ PZ
- Normal
- Hard as Hell

### 2. 双人

本地双人对战。

流程：

```text
玩家 1 选择角色
→ 玩家 2 选择角色
→ 选择球场
→ 开始比赛
```

### 3. 训练营

单人自由练习模式。

特点：

- 没有 AI
- 没有胜负
- 没有结束分数
- 可以无限练习投篮、扣篮和角色技能
- `TAB`：篮球直接回到手里
- `R`：重置篮球
- `ESC`：返回

训练营会显示：

- 命中数
- 得分
- 扣篮数

---

## 当前角色

### DJH

速度型角色。

**专属技能：Lightning Dash**

- 快速向前冲刺
- 可以撞开对手
- 命中时可以让对手掉球
- 技能键：玩家 1 `Left Shift` / 玩家 2 `Right Ctrl`

### Gorilla

力量型角色。

**专属技能：Ground Slam**

- 释放地面震击
- 击飞附近对手
- 可以震掉对手手中的篮球
- 技能带有震屏和视觉反馈

### Ninja

敏捷型角色。

**专属技能：Shadow Jump**

- 可以在空中进行二段跳
- 适合抢篮板、盖帽和空中进攻

---

## 操作方式

### 玩家 1

| 操作 | 按键 |
|---|---|
| 左右移动 | `A / D` |
| 跳跃 / 盖帽 / 抢篮板 / 扣篮 | `W` |
| 投篮 / 蓄力投篮 | `Space` |
| 抢断 / 捡球 | `S` |
| 角色技能 | `Left Shift` |

### 玩家 2

| 操作 | 按键 |
|---|---|
| 左右移动 | `← / →` |
| 跳跃 / 盖帽 / 抢篮板 / 扣篮 | `↑` |
| 投篮 / 蓄力投篮 | `Enter` |
| 抢断 / 捡球 | `↓` |
| 角色技能 | `Right Ctrl` |

### 通用操作

| 操作 | 按键 |
|---|---|
| 暂停比赛 | `ESC` |
| 返回上一页 | `Q / ESC` |
| 确认选项 | `Enter / Space` |
| 菜单选择 | `W / S` 或方向键 |
| 训练营篮球回手 | `TAB` |
| 训练营重置篮球 | `R` |

菜单同时支持鼠标悬停和点击。

---

## 投篮系统

游戏使用蓄力投篮机制。

- 长按投篮键开始蓄力
- 在绿色区域松开可以获得更稳定的投篮
- 松开过早会投短
- 松开过晚会投长
- 蓄力满后会自动出手

三个角色拥有不同的投篮节奏：

- DJH：完美区域较宽，稳定性较高
- Gorilla：蓄力较慢，完美区域较窄
- Ninja：蓄力较快，完美区域中等

---

## 扣篮系统

扣篮不是简单的篮下得分。

必须满足：

1. 玩家持球起跳
2. 篮球先到篮筐上方
3. 玩家下落
4. 篮球从上往下穿过篮筐

当前篮筐高度已调整，让三个角色都可以完成正常扣篮。

---

## 盖帽与篮板

### 盖帽

玩家跳起后，如果手部与投出的篮球接触，可以完成盖帽。

盖帽会触发：

- `BLOCK!` 提示
- 粒子效果
- 屏幕震动
- 篮球方向改变

### 篮板

篮球撞击篮筐或篮板后，跳起的玩家可以抢到篮板。

篮板会触发：

- `REBOUND!` 提示
- 篮球重新进入持球状态

---

## 得分规则

- 三分线内进球：1 分
- 三分线外进球：2 分
- 扣篮：按当前扣篮规则计分
- 先达到目标分数的玩家获胜

篮球必须从篮筐上方向下穿过，才会被判定为进球。

---

## 球场

当前包含三张地图：

### Sunset Street

黄昏街头篮球场。

### Neon Gym

霓虹风格室内球馆。

### Moon Rooftop

夜晚城市屋顶球场。

球场资源目录：

```text
assets/arenas/
├── street/
│   └── background.png
├── gym/
│   └── background.png
└── rooftop/
    └── background.png
```

篮筐资源：

```text
assets/props/hoop.png
```

---

## 本地化

游戏支持自由切换：

- English
- 简体中文

语言设置会自动保存。

语言文件：

```text
lang/
├── en.json
└── zh.json
```

游戏中的菜单、设置、角色、球场、暂停、结算和技能提示都通过语言文件读取。

---

## 人物动画

当前人物使用 Sprite Sheet 动画。

人物对应关系：

| 游戏角色 | 当前模型 |
|---|---|
| DJH | Fighter |
| Gorilla | Samurai |
| Ninja | Shinobi |

动画状态包括：

```text
idle
walk
run
jump
attack_1
attack_2
attack_3
hurt
shield
```

角色资源目录：

```text
assets/characters/
├── djh/
├── gorilla/
└── ninja/
```

---

## 运行环境

推荐环境：

- Python 3.11+
- Pygame 2.6+

安装依赖：

```bash
python -m pip install pygame
```

运行游戏：

```bash
cd "/Users/dujinhao/Documents/basketball-brawl"
python main.py
```

使用指定 Python 环境运行：

```bash
/Users/dujinhao/anaconda3/bin/python main.py
```

---

## 项目结构

```text
basketball-brawl/
├── main.py
├── game.py
├── player.py
├── ball.py
├── ai.py
├── animation.py
├── arenas.py
├── characters.py
├── constants.py
├── entities.py
├── feedback.py
├── localization.py
├── settings.py
├── ui.py
│
├── assets/
│   ├── characters/
│   ├── arenas/
│   ├── props/
│   └── ball.png
│
├── lang/
│   ├── en.json
│   └── zh.json
│
├── README.md
└── LATEST_UPDATE.txt
```

---

## 开发目标

后续计划：

- 完善角色投篮、扣篮和盖帽专属动作
- 加入音效和背景音乐
- 优化篮球旋转和篮网动画
- 优化 HUD、暂停页和比赛结算页
- 增加数据统计和成就
- 打包 Windows / macOS 可执行版本
- 准备 Steam Demo

---

## GitHub

提交当前版本：

```bash
git status
git add .
git commit -m "Release V3.0: Update gameplay, training camp and character animations"
git push origin main
```

创建版本标签：

```bash
git tag v3.0
git push origin v3.0
```

---

## 开发者

**Created and developed by Jinhao Du (David)**

中文署名：**杜近豪**

技术：

- Python
- Pygame

Copyright © 2026 Jinhao Du. All rights reserved.

---


