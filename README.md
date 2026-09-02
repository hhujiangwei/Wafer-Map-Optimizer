# Wafer Map Optimizer

晶圆芯片布局优化与导出工具。输入晶圆与芯片参数，计算晶圆内可容纳的最大芯片排布并可视化展示，支持导出图片、SINF3D 与 GDS/OAS 布局文件。

## 功能特性

- 两种布局模式：Fix Value（固定偏移）/ Auto（自动寻优）
- 可视化晶圆图：外轮廓、有效区、Notch、die 网格与坐标标注
- 框选缩放：左键拖拽放大、右键拖拽缩小，悬停显示坐标
- 统计显示距边缘最近的前 8 颗芯片距离（可点击标注）
- 导出：图片、SINF3D、GDS/OAS（SEMI-M1 标准 Notch，360 点轮廓）

## 环境要求

- Python 3
- PySide6、NumPy、Matplotlib、gdstk

## 安装依赖

```powershell
pip install pyside6 numpy matplotlib gdstk
```

## 运行

```powershell
python Wafer_Map_Optimizer.py
```

启动后默认全屏显示。

## 使用步骤

1. 在「Wafer Parameters」中设置晶圆直径、边缘排除、芯片尺寸与 Notch 朝向
2. 在「Centering」中选择模式：
   - **Fix Value**：设置 Offset X/Y，按固定偏移生成
   - **Auto**：选择 Optimize Step，自动寻优最大排布
3. 点击 `Generate Map` 生成布局，在「Analysis Results」查看行列数、总芯片数与距边距离
4. 使用下方按钮导出：Copy to Clipboard / Export Image / Export SINF3D / Export GDS/OAS

## 参数说明

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| Wafer Diameter (mm) | 300 | — | 晶圆直径 |
| Edge Exclusion (mm) | 3 | — | 边缘排除量 |
| Chip X (mm) | 32 | — | 芯片 X 方向尺寸 |
| Chip Y (mm) | 45 | — | 芯片 Y 方向尺寸 |
| Orientation | 180 | 0 / 90 / 180 / 270 | Notch 朝向 |
| Offset X / Offset Y (mm) | 0 | — | Fix Value 模式固定偏移 |
| Optimize Step (1/) | 4 | 1 / 2 / 4 / 5 / 10 | Auto 模式寻优步长分母 |

## GDS/OAS 导出说明

| 内容 | 规格 |
|------|------|
| Wafer 轮廓（layer 200） | 360 点多边形，切除 SEMI-M1 标准 Notch |
| EE 轮廓（layer 201） | 360 点多边形 |
| Chip（layer 101） | 芯片矩形轮廓 |
| Notch | V 型缺口、夹角 90°、径向切深 1.0 mm、槽底圆角 R=0.2 mm |

## 打包

```powershell
pyinstaller "Wafer Map Optimizer.spec"
```

## 项目文件

| 文件 | 说明 |
|------|------|
| `Wafer_Map_Optimizer.py` | 主程序 |
| `Wafer Map Optimizer.spec` | PyInstaller 打包配置 |
| `PRD.md` | 产品需求文档 |
| `软件技术文档.md` | 技术文档 |

## 技术栈

Python · PySide6 · NumPy · Matplotlib · gdstk · PyInstaller
