# HOOP HAVOC / 篮界狂潮

一款由 **Jinhao Du（David / 杜近豪）** 独立开发、使用 **Python + Pygame** 制作的 2D 街机街头篮球对战游戏。

玩家可以选择 DJH、BRAX、KAGE、DUKE，在 Sunset Court、Neon District、Skyline Arena 中进行投篮、扣篮、抢断、篮板、盖帽、角色技能与半场规则对抗。

> Current Build: **V3.3 Development Build**

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

### BRAX

力量型角色。

**专属技能：Ground Slam**

- 释放地面震击
- 击飞附近对手
- 可以震掉对手手中的篮球
- 技能带有震屏和视觉反馈

### KAGE

敏捷型角色。

**专属技能：Shadow Jump**

- 可以在空中进行二段跳
- 适合抢篮板、盖帽和空中进攻


### DUKE

战术型角色。

**专属技能：Blood Echo / Mirror Clone**

- 召唤 Blood Echo 作为临时队友
- DUKE 与 Blood Echo 可以互相传球
- 传球后控制权切换到接球者
- AI DUKE 会根据防守压力和传球线路使用分身
- Blood Echo 会独立跑位并参与进攻

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
| 传球 | `F` |

### 玩家 2

| 操作 | 按键 |
|---|---|
| 左右移动 | `← / →` |
| 跳跃 / 盖帽 / 抢篮板 / 扣篮 | `↑` |
| 投篮 / 蓄力投篮 | `Enter` |
| 抢断 / 捡球 | `↓` |
| 角色技能 | `Right Ctrl` |
| 传球 | `Right Shift` |

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

当前角色拥有不同的投篮节奏：

- DJH：完美区域较宽，稳定性较高
- BRAX：蓄力较慢，完美区域较窄
- KAGE：蓄力较快，完美区域中等

---

## 扣篮系统

扣篮不是简单的篮下得分。

必须满足：

1. 玩家持球起跳
2. 篮球先到篮筐上方
3. 玩家下落
4. 篮球从上往下穿过篮筐

当前篮筐高度已调整，让所有角色都可以完成正常扣篮。

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


### 防守篮板 CLEAR 规则

如果对方投篮不中并由你抢到防守篮板，必须先持球退出三分线，完成 CLEAR 后才能重新投篮或扣篮。

- 防守篮板：必须退出三分线
- 进攻篮板：无需重新退出三分线
- 未完成 CLEAR 时不能投篮或扣篮
- 屏幕会显示 `CLEAR THE BALL / 请出三分线`
- 越过三分线后显示 `CLEARED! / 已出三分线！`

### 14 秒 Shot Clock

- 获得新球权：14 秒
- 防守篮板：重置为 14 秒
- 进攻篮板：重置为 10 秒
- DUKE 与 Blood Echo 队内传球不会重置进攻时间
- 投篮离手后停止计时，允许压哨球完成飞行
- 进攻超时后球权交给对方并播放裁判哨声
- 困难 AI 在最后 3 秒进入紧急进攻，最后约 1.5 秒强制尝试出手


---

## 球场

当前包含三张地图：

### Sunset Court

黄昏街头篮球场。

### Neon District

霓虹风格室内球馆。

### Skyline Arena

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


## 音乐、音效与第三方素材

V3.3 已加入背景音乐与游戏音效系统，包括：

- 主菜单 BGM
- 比赛 BGM
- 比赛胜利音乐
- 空心入网声
- 打铁声
- 篮球反弹
- 篮板、扣篮、盖帽
- 角色技能音效
- 14 秒 Shot Clock 超时哨声

部分音乐与音效素材来源于 **Pixabay**：

https://pixabay.com/

素材按照各自对应的 Pixabay Content License 使用。

胜利音效：

**Winner game sound — PuyoPuyoMegaFan1234 / Pixabay**

来源页面：

https://pixabay.com/sound-effects/film-special-effects-winner-game-sound-404167/

正式发布时会继续保留第三方素材来源与授权记录。

---

### 音量控制

设置页面支持三层音量调节：

- 总音量（Master Volume）
- 音乐音量（Music Volume）
- 音效音量（SFX Volume）

角色选择阶段的 BGM 自动降低到当前音乐音量的 50%，离开选人页面后恢复。所有游戏音效统一使用同一个 SFX 音量，不再对单个音效使用独立音量倍率。

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
| BRAX | Samurai |
| KAGE | Shinobi |

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
- 继续扩充不同球场的独立 BGM 与角色专属音效
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


## 游戏创作与素材说明

**HOOP HAVOC / 篮界狂潮** 的游戏设计、程序实现、玩法平衡与项目开发由 **Jinhao Du（David / 杜近豪）** 完成。

开发技术：

- Python
- Pygame

第三方音乐与音效素材中，部分内容来自：

**Pixabay — https://pixabay.com/**

相关素材在游戏内 Credits 与本 README 中保留来源说明。

---

## 开发者

**Created and developed by Jinhao Du (David)**

中文署名：**杜近豪**

技术：

- Python
- Pygame

Copyright © 2026 Jinhao Du. All rights reserved.

---




## V3.5 比赛统计与结算系统

V3.5 进一步完善正式比赛体验：

- 正式采用 2 分 / 3 分计分规则
- 三分线外命中：3 分
- 三分线内命中：2 分
- 上篮与扣篮：2 分
- 率先达到 21 分的一方获胜
- 新增 PERFECT / GOOD / EARLY / LATE 投篮时机反馈
- 新增对局内操作按键 HUD
- 操作 HUD 支持 H 键显示 / 隐藏
- 操作 HUD 支持中文 / English 自动切换
- 新增比赛结束统计页面
- 新增 FG 投篮命中 / 出手统计
- 新增 3PT 三分命中 / 出手统计
- 新增篮板、抢断、盖帽与扣篮统计
- 优化比赛结束后的胜者展示与双方数据对比



## V3.6 比赛表现与上篮系统

V3.6 重点强化了比赛节奏、得分反馈和篮下终结体验。

### 上篮系统
- 新增篮筐前约两步的上篮起步区
- 新增上篮自动推进与收速逻辑
- 新增普通挑篮与打板上篮两种终结方式
- 高速突破更倾向打板上篮
- 慢速近筐更倾向柔和挑篮
- 无干扰上篮不再受到 AI 难度和随机命中率影响
- 优化上篮弧线，减少空篮擦框和低平撞筐
- 防守篮板未完成 CLEAR 时仍禁止直接上篮得分

### 篮筐与扣篮
- 三张球场篮筐整体上移
- 人物模型高度保持不变
- 跳跃参数保持不变
- 保留跳起后从上往下完成扣篮的判定

### 得分反馈
- 两分与三分使用不同的视觉反馈
- 三分命中特效展示时间延长
- 上篮保持较轻的镜头反馈
- 两分使用轻微震动
- 三分使用更明显的冲击反馈
- 扣篮继续保持最强的得分表现

### 比赛节奏
- 进球后增加短暂展示时间
- 让上篮、扣篮、三分等动作和特效更容易看清
- 操作 HUD 开局自动显示后淡出
- H 键可随时重新显示或隐藏操作提示

### 音频
- 更新 DUKE Clone 分身音效
- 保留统一音量系统与独立音效层级

