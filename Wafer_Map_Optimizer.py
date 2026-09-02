import io
import os
import sys

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Polygon, Rectangle

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QImage
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def resource_path(relative_path):
    """获取资源的路径，支持打包后的应用"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


icon_path = resource_path("temp_icon.ico")

GROUPBOX_STYLE = (
    "QGroupBox { border: 1px solid #C8C8C8; margin-top: 0.5em; } "
    "QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 2px; }"
)


class ClickableLabel(QLabel):
    """可响应左键点击的标签，点击时发出对应序号"""
    clicked = Signal(int)

    def __init__(self, index, text="", parent=None):
        super().__init__(text, parent)
        self._index = index

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._index)
        super().mousePressEvent(event)


class FinalWaferAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wafer Map Optimizer")
        self.resize(1600, 1000)
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.entries = {}
        self.stats_labels = {}
        self.current_layout = None
        self.current_params = None
        self._base_xlim = None
        self._base_ylim = None
        self._dist_visible = [False] * 8
        self._dist_artists = []
        self._hover_text = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 左侧控制面板（固定宽度）
        self.control_panel = QWidget()
        self.control_panel.setFixedWidth(320)
        control_layout = QVBoxLayout(self.control_panel)
        control_layout.setContentsMargins(5, 5, 5, 5)
        control_layout.setSpacing(5)

        control_layout.addWidget(self.create_parameter_inputs())
        control_layout.addWidget(self.create_centering_controls())
        control_layout.addWidget(self.create_operation_controls())
        control_layout.addWidget(self.create_results_display())
        control_layout.addLayout(self.create_action_buttons())
        control_layout.addStretch()

        # 右侧可视化画布
        self.fig = Figure(figsize=(12, 12), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)

        main_layout.addWidget(self.control_panel)
        main_layout.addWidget(self.canvas, stretch=1)

        # 交互事件
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)

        # 框选缩放状态
        self._drag_start = None
        self._drag_rect = None

        # 状态栏与进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(120)
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().showMessage("就绪")

    def create_parameter_inputs(self):
        """创建参数输入控件（仅晶圆/芯片几何参数）"""
        group = QGroupBox("Wafer Parameters")
        group.setStyleSheet(GROUPBOX_STYLE)
        form = QFormLayout(group)

        for label, name, default in [
            ("Wafer Diameter (mm):", "wafer_dia", "300"),
            ("Edge Exclusion (mm):", "edge_excl", "3"),
            ("Chip X (mm):", "chip_x", "32"),
            ("Chip Y (mm):", "chip_y", "45"),
        ]:
            edit = QLineEdit(default)
            self.entries[name] = edit
            form.addRow(label, edit)

        notch = QComboBox()
        notch.addItems(["0", "90", "180", "270"])
        notch.setCurrentText("180")
        self.entries["notch_angle"] = notch
        form.addRow("Orientation:", notch)

        return group

    def create_centering_controls(self):
        """创建 Centering groupbox：Fix Value / Auto 两个 tab"""
        group = QGroupBox("Centering")
        group.setStyleSheet(GROUPBOX_STYLE)

        self.centering_tabs = QTabWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.centering_tabs)

        # Tab 1: Fix Value（固定偏移）
        fix_tab = QWidget()
        fix_form = QFormLayout(fix_tab)
        offset_x = QLineEdit("0")
        offset_y = QLineEdit("0")
        self.entries["offset_x"] = offset_x
        self.entries["offset_y"] = offset_y
        fix_form.addRow("Offset X (mm):", offset_x)
        fix_form.addRow("Offset Y (mm):", offset_y)
        self.centering_tabs.addTab(fix_tab, "Fix Value")

        # Tab 2: Auto（自动寻优）
        auto_tab = QWidget()
        auto_form = QFormLayout(auto_tab)
        step = QComboBox()
        step.addItems(["1", "2", "4", "5", "10"])
        step.setCurrentText("4")
        self.entries["optimize_step"] = step
        auto_form.addRow("Optimize Step (1/):", step)
        self.centering_tabs.addTab(auto_tab, "Auto")

        return group

    def create_operation_controls(self):
        """创建 Generate Map 按钮（位于 Wafer Parameters 下方，横向占满）"""
        self.generate_btn = QPushButton("Generate Map")
        self.generate_btn.setFixedHeight(45)
        self.generate_btn.clicked.connect(self.run_optimization)
        return self.generate_btn

    def create_action_buttons(self):
        """Analysis Results 下方竖排功能按钮（每行独占满）"""
        layout = QVBoxLayout()

        self.min_dist_btn = QPushButton("Show/Hide min Distance")
        self.min_dist_btn.setFixedHeight(45)
        self.min_dist_btn.setCheckable(True)
        self.min_dist_btn.setChecked(False)
        self.min_dist_btn.clicked.connect(self.on_min_dist_toggled)
        layout.addWidget(self.min_dist_btn)

        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setFixedHeight(45)
        copy_btn.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(copy_btn)

        export_img_btn = QPushButton("Export Image")
        export_img_btn.setFixedHeight(45)
        export_img_btn.clicked.connect(self.export_image)
        layout.addWidget(export_img_btn)

        export_sinf_btn = QPushButton("Export SINF3D")
        export_sinf_btn.setFixedHeight(45)
        export_sinf_btn.clicked.connect(self.export_sinf)
        layout.addWidget(export_sinf_btn)

        return layout

    def create_results_display(self):
        """创建结果展示区域"""
        group = QGroupBox("Analysis Results")
        group.setStyleSheet(GROUPBOX_STYLE)
        form = QFormLayout(group)

        stats = [
            ("Column Count:", "colqty"),
            ("Row Count:", "rowqty"),
            ("Total Dies:", "count"),
            ("Optimal Offset:", "best_offset"),
        ]
        dist_names = [f"min_dist{i}" for i in range(1, 9)]
        stats += [(f"Min Dist {i}:", name) for i, name in enumerate(dist_names, start=1)]

        for label, name in stats:
            if name in dist_names:
                value_label = ClickableLabel(dist_names.index(name))
                value_label.setCursor(Qt.PointingHandCursor)
                value_label.clicked.connect(self.on_dist_label_clicked)
            else:
                value_label = QLabel("")
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.stats_labels[name] = value_label
            if name == "best_offset":
                self.offset_label = QLabel(label)
                form.addRow(self.offset_label, value_label)
            else:
                form.addRow(label, value_label)

        return group

    def run_optimization(self):
        """执行寻优流程"""
        self.generate_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.statusBar().showMessage("计算中...")
        QApplication.processEvents()
        try:
            params = self.get_parameters()
            mode = 'fixed' if self.centering_tabs.currentIndex() == 0 else 'auto'
            if mode == 'fixed':
                offset_x, offset_y = self.get_fixed_offset()
                best = self.generate_tile_layout(params, offset_x, offset_y)
            else:
                best = self.find_optimal_offset(params)
            self.current_mode = mode
            self.current_layout = best
            self.current_params = params
            if best is None or best['count'] == 0:
                self.clear_results()
                self.draw_wafermap(params, best, mode)
                self.statusBar().showMessage("未找到有效芯片布局")
            else:
                self.update_display(best, mode)
                self.draw_wafermap(params, best, mode)
                self.statusBar().showMessage(f"完成：共 {best['count']} 颗芯片")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.statusBar().showMessage("计算失败")
        finally:
            self.generate_btn.setEnabled(True)
            self.progress.setVisible(False)

    def clear_results(self):
        """清空结果展示（空布局时）"""
        for name, lbl in self.stats_labels.items():
            if name in ("colqty", "rowqty", "count"):
                lbl.setText("0")
            else:
                lbl.setText("N/A")

    def get_parameters(self):
        """读取并校验参数"""
        def positive_float(name, label):
            raw = self.entries[name].text().strip()
            try:
                value = float(raw)
            except ValueError:
                raise ValueError(f"{label} 必须是数字")
            if value <= 0:
                raise ValueError(f"{label} 必须大于 0")
            return value

        params = {
            'wafer_dia': positive_float('wafer_dia', 'Wafer Diameter'),
            'edge_excl': positive_float('edge_excl', 'Edge Exclusion'),
            'chip_x': positive_float('chip_x', 'Chip X'),
            'chip_y': positive_float('chip_y', 'Chip Y'),
            'notch_angle': int(self.entries['notch_angle'].currentText()),
            'optimize_step': int(self.entries['optimize_step'].currentText()),
        }

        wafer_radius = params['wafer_dia'] / 2
        if params['edge_excl'] >= wafer_radius:
            raise ValueError("Edge Exclusion 必须小于晶圆半径")

        return params

    def get_fixed_offset(self):
        """读取固定模式下的 Offset X / Offset Y（可为任意数值）"""
        def any_float(name, label):
            raw = self.entries[name].text().strip()
            try:
                return float(raw)
            except ValueError:
                raise ValueError(f"{label} 必须是数字")

        return (any_float('offset_x', 'Offset X'), any_float('offset_y', 'Offset Y'))

    def find_optimal_offset(self, params):
        """核心寻优算法"""
        chip_x, chip_y = params['chip_x'], params['chip_y']
        base_offsets = [(0, 0), (chip_x / 2, 0), (0, chip_y / 2), (chip_x / 2, chip_y / 2)]
        best = None

        for offset in base_offsets + self.generate_adaptive_offsets(chip_x, chip_y, params['optimize_step']):
            layout = self.generate_tile_layout(params, *offset)
            if best is None or layout['count'] > best['count']:
                best = layout
        return best

    def generate_adaptive_offsets(self, chip_x, chip_y, step):
        """生成自适应偏移候选"""
        step_x = chip_x / int(step)
        step_y = chip_y / int(step)
        return [(x, y) for x in np.arange(0, chip_x, step_x)
                for y in np.arange(0, chip_y, step_y)
                if (x, y) not in [(0, 0), (chip_x / 2, 0), (0, chip_y / 2), (chip_x / 2, chip_y / 2)]]

    def generate_tile_layout(self, params, offset_x, offset_y):
        """生成带坐标映射的芯片布局"""
        wafer_radius = params['wafer_dia'] / 2
        eff_radius = wafer_radius - params['edge_excl']
        chip_x, chip_y = params['chip_x'], params['chip_y']

        positions = []
        coord_map = {}
        die_margins = {}
        current_ring = 0

        while True:
            ring_added = False
            for dx in range(-current_ring, current_ring + 1):
                for dy in range(-current_ring, current_ring + 1):
                    x = dx * chip_x + offset_x
                    y = dy * chip_y + offset_y

                    if (x, y) not in positions and self.is_valid_position(x, y, chip_x, chip_y, eff_radius):
                        positions.append((x, y))
                        coord_map[(x, y)] = (dx, dy)
                        ring_added = True
                        # 记录每颗 die 的最贴边角与其余量
                        mind, corner = self.compute_die_margin(x, y, chip_x, chip_y, eff_radius)
                        die_margins[(x, y)] = (mind, corner)

            if not ring_added:
                break
            current_ring += 1

        # 前八颗距离有效边缘最近的芯片
        nearest_dies = []
        for mind, pos in sorted(((die_margins[p][0], p) for p in positions), key=lambda t: t[0])[:8]:
            col, row = coord_map[pos]
            nearest_dies.append({
                'x': pos[0], 'y': pos[1], 'col': col, 'row': row,
                'dist': mind, 'corner': die_margins[pos][1],
            })

        return {
            'positions': positions,
            'coord_map': coord_map,
            'count': len(positions),
            'offset': (offset_x, offset_y),
            'min_dists': [d['dist'] for d in nearest_dies],
            'die_margins': die_margins,
            'nearest_dies': nearest_dies,
        }

    def compute_die_margin(self, x, y, dx, dy, eff_radius):
        """返回芯片四角中最小余量及其角坐标"""
        corners = [
            (x + dx / 2, y + dy / 2),
            (x + dx / 2, y - dy / 2),
            (x - dx / 2, y + dy / 2),
            (x - dx / 2, y - dy / 2),
        ]
        dists = [eff_radius - np.hypot(cx, cy) for cx, cy in corners]
        i = int(np.argmin(dists))
        return dists[i], corners[i]

    def is_valid_position(self, x, y, dx, dy, radius):
        """校验芯片四角是否均在有效圆内"""
        half_dx = dx / 2
        half_dy = dy / 2
        corners = [
            (x + half_dx, y + half_dy),
            (x + half_dx, y - half_dy),
            (x - half_dx, y + half_dy),
            (x - half_dx, y - half_dy),
        ]
        return all(cx ** 2 + cy ** 2 <= radius ** 2 for cx, cy in corners)

    def update_display(self, best, mode='auto'):
        """更新结果展示"""
        cols = [col for (col, _) in best['coord_map'].values()]
        rows = [row for (_, row) in best['coord_map'].values()]
        col_ct = max(cols) - min(cols) + 1
        row_ct = max(rows) - min(rows) + 1

        self.offset_label.setText("Offset:" if mode == 'fixed' else "Optimal Offset:")
        self.stats_labels['colqty'].setText(str(col_ct))
        self.stats_labels['rowqty'].setText(str(row_ct))
        self.stats_labels['count'].setText(str(best['count']))
        self.stats_labels['best_offset'].setText(f"({best['offset'][0]:.2f}, {best['offset'][1]:.2f})")

        distances = best.get('min_dists', [])
        for i in range(8):
            name = f"min_dist{i + 1}"
            if len(distances) > i:
                self.stats_labels[name].setText(f"{distances[i]:.3f} mm")
            else:
                self.stats_labels[name].setText("N/A")

    def draw_wafermap(self, params, layout, mode='auto'):
        """绘制带标注的晶圆图（fixed=深蓝，auto=绿色芯片轮廓）"""
        self.ax.clear()
        wafer_radius = params['wafer_dia'] / 2

        # 晶圆外轮廓与有效区
        self.ax.add_patch(Circle((0, 0), wafer_radius, ec='black', fc='none', lw=1))
        self.ax.add_patch(Circle((0, 0), wafer_radius - params['edge_excl'],
                                 ec='red', fc='none', ls='--', lw=0.8))

        # Notch
        self.draw_notch(params['notch_angle'], wafer_radius)

        # 中心十字参考线
        cross_size = 2.5
        self.ax.plot([-cross_size, cross_size], [cross_size, -cross_size],
                     color='red', ls=':', lw=0.8, alpha=0.7)
        self.ax.plot([-cross_size, cross_size], [-cross_size, cross_size],
                     color='red', ls=':', lw=0.8, alpha=0.7)

        # 芯片网格（fixed 保持当前深蓝，auto 使用绿色）
        edge_color = '#1F4E79' if mode == 'fixed' else '#2E7D32'
        chip_x, chip_y = params['chip_x'], params['chip_y']
        for (x, y), (col, row) in layout['coord_map'].items():
            rect = Rectangle((x - chip_x / 2, y - chip_y / 2), chip_x, chip_y,
                             facecolor='white', edgecolor=edge_color, lw=0.4)
            self.ax.add_patch(rect)

        # 坐标标注
        self.add_coordinate_labels(layout['coord_map'], chip_x, chip_y, wafer_radius)

        # 前八颗芯片的距边标注（默认隐藏）
        self.draw_dist_annotations(layout)

        # 悬停坐标提示（画布内右上角，默认隐藏）
        self._hover_text = self.ax.text(
            0.98, 0.98, "", transform=self.ax.transAxes, ha='right', va='top',
            fontsize=10, color='black',
            bbox=dict(boxstyle='round,pad=0.3', fc='#FAFAFA', ec='#C8C8C8', alpha=0.9),
            visible=False,
        )

        # 绘图范围
        lim = wafer_radius * 1.1
        self.ax.set_xlim(-lim, lim)
        self.ax.set_ylim(-lim, lim)
        self.ax.set_aspect('equal')
        self.ax.axis('off')

        # 尽量占满画布
        self.fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
        self._base_xlim = (-lim, lim)
        self._base_ylim = (-lim, lim)

        self.canvas.draw()

    def draw_dist_annotations(self, layout):
        """绘制前八颗芯片的垂线标注（初始隐藏）"""
        self._dist_artists = []
        self._dist_visible = [False] * 8
        if hasattr(self, 'min_dist_btn'):
            self.min_dist_btn.setChecked(False)
        if not layout or layout['count'] == 0 or not layout.get('nearest_dies'):
            return

        eff_radius = self.current_params['wafer_dia'] / 2 - self.current_params['edge_excl']
        for info in layout['nearest_dies']:
            cx, cy = info['corner']
            h = np.hypot(cx, cy)
            if h == 0:
                continue
            ex = cx / h * eff_radius
            ey = cy / h * eff_radius
            line, = self.ax.plot([cx, ex], [cy, ey], color='#FF0000', lw=1, ls='--')
            text = self.ax.text((cx + ex) / 2, (cy + ey) / 2, f"{info['dist']:.3f} mm",
                                color='#FF0000', fontsize=8, ha='left', va='bottom')
            line.set_visible(False)
            text.set_visible(False)
            self._dist_artists.append([line, text])

    def on_dist_label_clicked(self, index):
        """左键点击 Min Dist label，切换对应标注显示/隐藏"""
        if not self.current_layout or index >= len(self._dist_artists):
            return
        self._dist_visible[index] = not self._dist_visible[index]
        for artist in self._dist_artists[index]:
            artist.set_visible(self._dist_visible[index])
        self.canvas.draw_idle()

    def on_min_dist_toggled(self, checked):
        """全局显示/隐藏所有最小距离标注"""
        if not self.current_layout or self.current_layout['count'] == 0:
            self.min_dist_btn.setChecked(False)
            QMessageBox.information(self, "Info", "请先点击 Generate Map 生成地图")
            return
        for i in range(len(self._dist_artists)):
            self._dist_visible[i] = checked
            for artist in self._dist_artists[i]:
                artist.set_visible(checked)
        self.canvas.draw_idle()

    def draw_notch(self, angle, wafer_radius):
        """按指定角度绘制 Notch"""
        angle_dict = {"0": 90, "90": 0, "180": 270, "270": 180}
        mapped_angle = angle_dict[str(angle)]
        notch_height = min(3, wafer_radius / 50)
        notch_width = min(3, wafer_radius / 50)
        p1_radius = wafer_radius - notch_height

        theta_p1 = np.radians(mapped_angle)
        theta_p2 = np.radians(mapped_angle) - np.arcsin(0.5 * notch_width / wafer_radius)
        theta_p3 = np.radians(mapped_angle) + np.arcsin(0.5 * notch_width / wafer_radius)
        base_p1_x = p1_radius * np.cos(theta_p1)
        base_p2_x = wafer_radius * np.cos(theta_p2)
        base_p3_x = wafer_radius * np.cos(theta_p3)
        base_p1_y = p1_radius * np.sin(theta_p1)
        base_p2_y = wafer_radius * np.sin(theta_p2)
        base_p3_y = wafer_radius * np.sin(theta_p3)

        points = [(base_p1_x, base_p1_y), (base_p2_x, base_p2_y), (base_p3_x, base_p3_y)]
        self.ax.add_patch(Polygon(points, closed=True, color='black'))

    def add_coordinate_labels(self, coord_map, chip_x, chip_y, wafer_radius):
        """添加 X/Y 坐标标注"""
        xs = sorted(dict.fromkeys([x for (x, _) in coord_map.keys()]))
        ys = sorted(dict.fromkeys([y for (_, y) in coord_map.keys()]))
        axis_shift = min(10, wafer_radius / 30)

        for i, x in enumerate(xs):
            self.ax.text(x, -axis_shift - wafer_radius, str(i),
                         ha='center', va='top', fontsize=8, color='black')
        for j, y in enumerate(ys):
            self.ax.text(-axis_shift - wafer_radius, y, str(j),
                         ha='right', va='center', fontsize=8, color='black')

    def on_press(self, event):
        """双击恢复初始视图；左/右键按下开始框选（左=放大，右=缩小）"""
        if event.dblclick and self._base_xlim is not None:
            self.ax.set_xlim(self._base_xlim)
            self.ax.set_ylim(self._base_ylim)
            self.canvas.draw_idle()
            return
        if (event.button in (1, 3) and event.inaxes == self.ax
                and event.xdata is not None and event.ydata is not None):
            color = '#1F4E79' if event.button == 1 else '#C00000'
            self._drag_start = (event.xdata, event.ydata, event.button)
            self._drag_rect = Rectangle((event.xdata, event.ydata), 0, 0,
                                        facecolor=color, edgecolor=color,
                                        alpha=0.15, lw=0.8)
            self.ax.add_patch(self._drag_rect)

    def on_release(self, event):
        """左键释放=放大到选框；右键释放=按选框比例缩小"""
        if event.button not in (1, 3) or self._drag_start is None:
            return
        start_x, start_y, button = self._drag_start
        self._drag_start = None
        if self._drag_rect is not None:
            self._drag_rect.remove()
            self._drag_rect = None

        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            self.canvas.draw_idle()
            return

        x0, x1 = min(start_x, event.xdata), max(start_x, event.xdata)
        y0, y1 = min(start_y, event.ydata), max(start_y, event.ydata)
        w = x1 - x0
        h = y1 - y0
        if w <= 0 or h <= 0:
            self.canvas.draw_idle()
            return

        # 忽略过小的拖拽（防误触），按像素判断
        px0, py0 = self.ax.transData.transform((x0, y0))
        px1, py1 = self.ax.transData.transform((x1, y1))
        if abs(px1 - px0) < 8 or abs(py1 - py0) < 8:
            self.canvas.draw_idle()
            return

        if button == 1:
            # 左键：选框区域放大为当前视图
            self.ax.set_xlim(x0, x1)
            self.ax.set_ylim(y0, y1)
        else:
            # 右键：按选框与视口的像素比例缩小
            ax_w = self.ax.bbox.width
            ax_h = self.ax.bbox.height
            box_w = abs(px1 - px0)
            box_h = abs(py1 - py0)
            factor = max(ax_w / box_w, ax_h / box_h)
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            dx = (xlim[1] - xlim[0]) / 2 * factor
            dy = (ylim[1] - ylim[0]) / 2 * factor
            self.ax.set_xlim(cx - dx, cx + dx)
            self.ax.set_ylim(cy - dy, cy + dy)
        self.canvas.draw_idle()

    def on_motion(self, event):
        """鼠标悬停：显示坐标；拖拽框选时绘制选框"""
        if self._drag_start is not None and event.inaxes == self.ax:
            if self._drag_rect is not None and event.xdata is not None and event.ydata is not None:
                x0, y0, _ = self._drag_start
                self._drag_rect.set_xy((min(x0, event.xdata), min(y0, event.ydata)))
                self._drag_rect.set_width(abs(event.xdata - x0))
                self._drag_rect.set_height(abs(event.ydata - y0))
                self.canvas.draw_idle()
            return
        if self._hover_text is None:
            return
        x, y = event.xdata, event.ydata
        if event.inaxes != self.ax or x is None or y is None:
            if self._hover_text.get_visible():
                self._hover_text.set_visible(False)
                self.canvas.draw_idle()
            return
        self._hover_text.set_text(f"X: {x:.3f} mm    Y: {y:.3f} mm")
        if not self._hover_text.get_visible():
            self._hover_text.set_visible(True)
        self.canvas.draw_idle()

    def copy_to_clipboard(self):
        """复制当前画布图片到剪贴板"""
        if not self.current_layout or self.current_layout['count'] == 0:
            QMessageBox.warning(self, "Warning", "请先点击 Generate Map 生成地图")
            return
        try:
            buf = io.BytesIO()
            self.fig.savefig(buf, format='png', dpi=150,
                             bbox_inches='tight', facecolor=self.fig.get_facecolor())
            buf.seek(0)
            img = QImage.fromData(buf.getvalue())
            QGuiApplication.clipboard().setImage(img)
            self.statusBar().showMessage("画布已复制到剪贴板")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def export_image(self):
        """导出当前画布图片"""
        if not self.current_layout or self.current_layout['count'] == 0:
            QMessageBox.warning(self, "Warning", "请先点击 Generate Map 生成地图")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", "", "PNG image (*.png);;JPEG image (*.jpg);;All files (*.*)"
        )
        if not file_path:
            return
        try:
            self.fig.savefig(file_path, dpi=150,
                             bbox_inches='tight', facecolor=self.fig.get_facecolor())
            QMessageBox.information(self, "Success", "图片导出成功")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def export_sinf(self):
        """导出 SINF 格式布局文件"""
        if not self.current_layout or self.current_layout['count'] == 0:
            QMessageBox.warning(self, "Warning", "Please generate a map first")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export SINF3D Layout", "", "SINF files (*.txt);;All files (*.*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w') as f:
                f.write(self.generate_sinf_content())
            QMessageBox.information(self, "Success", "SINF file exported successfully")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def generate_sinf_content(self):
        """生成 SINF 文件内容"""
        if not self.current_layout:
            return ""

        params = self.get_parameters()
        coord_map = self.current_layout['coord_map']

        cols = [col for (col, _) in coord_map.values()]
        rows = [row for (_, row) in coord_map.values()]
        col_ct = max(cols) - min(cols) + 1
        row_ct = max(rows) - min(rows) + 1

        map_grid = [["___" for _ in range(col_ct)] for _ in range(row_ct)]
        for (col, row) in coord_map.values():
            col = col - min(cols)
            row = row - min(rows)
            map_grid[row][col] = "000"

        content = [
            "DEVICE:",
            "LOT:",
            "WAFER:",
            f"FNLOC:{self.entries['notch_angle'].currentText()}",
            f"ROWCT:{row_ct}",
            f"COLCT:{col_ct}",
            "BCEQU:000",
            "REFPX:0",
            "REFPY:0",
            "DUTMS:mm",
            f"XDIES:{params['chip_x']}",
            f"YDIES:{params['chip_y']}"
        ]

        for row in reversed(map_grid):
            content.append("RowData:" + " ".join(row))

        return "\n".join(content)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FinalWaferAnalyzer()
    window.show()
    sys.exit(app.exec())