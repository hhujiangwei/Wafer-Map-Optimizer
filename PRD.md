# Wafer Map Optimizer 产品需求文档（PRD）

## 1. 产品概述

晶圆芯片布局优化与导出工具。输入晶圆与芯片参数后，计算晶圆内可容纳的最大芯片排布，可视化展示布局，并支持导出图片、SINF3D 与 GDS/OAS 布局文件。

## 2. 目标用户

需要规划芯片在晶圆上排布并导出布局文件的相关工程人员。

## 3. 功能需求

### 3.1 参数输入

| 模块 | 参数 | 说明 |
|------|------|------|
| Wafer Parameters | Wafer Diameter、Edge Exclusion、Chip X、Chip Y、Orientation | 晶圆几何与芯片尺寸、Notch 朝向 |
| Centering – Fix Value | Offset X、Offset Y | 固定偏移模式，按指定偏移生成布局 |
| Centering – Auto | Optimize Step | 自动寻优模式，网格枚举偏移寻找最大芯片数 |

### 3.2 地图生成

- `Generate Map` 根据当前 Centering 模式生成布局：
  - Fix Value 模式使用固定偏移算法
  - Auto 模式使用自动寻优算法
- 计算并展示：列数、行数、总芯片数、偏移量、距边缘最近的前 8 颗芯片距离。

### 3.3 可视化

- 晶圆外轮廓、有效区、Notch、die 网格与坐标标注。
- 左键拖拽框选放大、右键拖拽框选缩小；鼠标悬停显示坐标。
- 点击「Min Dist」标签切换对应芯片的距边标注显示。
- 不同模式芯片轮廓颜色区分：Fix Value 深蓝、Auto 绿色。

### 3.4 导出

| 功能 | 说明 |
|------|------|
| Copy to Clipboard | 复制当前画布到剪贴板 |
| Export Image | 导出画布为 PNG / JPG |
| Export SINF3D | 导出布局为 SINF 文本格式 |
| Export GDS/OAS | 导出 GDSII / OASIS 布局文件 |

GDS/OAS 导出规范：

- Chip 单元（layer 101）：单颗芯片矩形轮廓。
- Wafer 轮廓（layer 200）：360 点多边形，并按 SEMI-M1 标准切除 Notch。
- EE 轮廓（layer 201）：360 点多边形。
- Notch 规格：V 型缺口、夹角 90°、径向切深 1.0 mm、槽底圆角 R=0.2 mm。

### 3.5 界面与交互

- 启动后默认全屏显示。
- 参数非法（非数字、非正数、Edge Exclusion 不小于半径）时给出错误提示。
- 计算期间 Generate Map 按钮置灰并显示进度反馈。

## 4. 非功能需求

- 轻量依赖：Python + PySide6 + NumPy + Matplotlib + gdstk。
- 支持 PyInstaller 打包为单文件可执行程序。
- 界面布局紧凑固定，控件不重叠。
