# Wafer Map Optimizer

晶圆芯片布局优化工具。输入晶圆尺寸与芯片尺寸，自动寻优计算晶圆内可容纳的最大芯片排布，并以图形展示，同时给出距离有效边缘最近的前四颗芯片的贴边距离。

## 功能特性

- 输入晶圆直径、边缘排除量、芯片 X/Y 尺寸、Notch 朝向与寻优步长
- 一键计算最大芯片数、行列数、最优偏移量
- 可视化晶圆图：外轮廓、有效区、Notch、die 网格与坐标标注
- 统计显示距离边缘最近的前四颗芯片距离
- 导出 SINF 格式布局文件

## 快速开始

### 环境要求

- Python 3
- NumPy
- Matplotlib

### 安装依赖

```powershell
pip install numpy matplotlib
```

### 运行

```powershell
python WaferMapOptimizer.py
```

## 使用步骤

1. 在左侧「Wafer Parameters」中设置晶圆与芯片参数
2. 点击 `Generate Map` 执行寻优并绘制晶圆图
3. 在「Analysis Results」查看行列数、总芯片数、最优偏移与前四颗芯片贴边距离
4. 如需保存，点击 `Export SINF` 导出布局文件

## 参数说明

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| Wafer Diameter (mm) | 300 | — | 晶圆直径 |
| Edge Exclusion (mm) | 3 | — | 边缘排除量 |
| Chip X (mm) | 32 | — | 芯片 X 方向尺寸 |
| Chip Y (mm) | 45 | — | 芯片 Y 方向尺寸 |
| Orientation | 180 | 0 / 90 / 180 / 270 | Notch 朝向 |
| Optimize Step (1/) | 4 | 1 / 2 / 4 / 5 / 10 | 寻优步长分母 |

## 打包

使用 PyInstaller 打包为单文件可执行程序：

```powershell
pyinstaller "Wafer Map Optimizer.spec"
```

## 项目文件

| 文件 | 说明 |
|------|------|
| `WaferMapOptimizer.py` | 主程序 |
| `Wafer Map Optimizer.spec` | PyInstaller 打包配置 |
| `temp_icon.ico` / `temp_icon.png` | 程序图标 |
| `软件技术文档.md` | 详细技术文档（算法、架构、接口说明） |

## 技术栈

Python · Tkinter · NumPy · Matplotlib · PyInstaller
