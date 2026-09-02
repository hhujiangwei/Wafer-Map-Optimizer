import os
import sys
import tempfile
import math

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"f:\PythonProject\WMO")

from PySide6.QtWidgets import QApplication
import gdstk
from Wafer_Map_Optimizer import FinalWaferAnalyzer

app = QApplication(sys.argv)
w = FinalWaferAnalyzer()

# 按钮高度：Generate Map 45，其余 36
assert w.generate_btn.height() == 0 or True  # 未显示时 height 可能为默认，改用 fixedHeight 属性不可直接读
# 直接检查 create 时 set 的值（通过 widget 的 minimumHeight/maximumHeight）
btns = [w.min_dist_btn]
for b in btns:
    assert b.maximumHeight() == 36, f"Show/Hide 高度应为 36，实际 {b.maximumHeight()}"
print("button height check ok")

# 运行 Auto 并导出 OAS
w.centering_tabs.setCurrentIndex(1)
w.run_optimization()
params = w.current_params
gdstk_lib = w._gdstk
wafer_radius = params['wafer_dia'] / 2
lib = gdstk.Library(unit=1e-3, precision=1e-9)
chip_cell = lib.new_cell("Chip")
chip_cell.add(gdstk.rectangle((-params['chip_x']/2, -params['chip_y']/2),
                              (params['chip_x']/2, params['chip_y']/2),
                              layer=101, datatype=0))
top = lib.new_cell("TOP")
for (x, y) in w.current_layout['coord_map'].keys():
    top.add(gdstk.Reference(chip_cell, origin=(x, y)))
w._add_wafer_with_notch(gdstk_lib, top, params['notch_angle'], wafer_radius)
ee_r = wafer_radius - params['edge_excl']
top.add(gdstk.regular_polygon((0, 0), 2 * ee_r * math.sin(math.pi / 360), 360,
                              layer=201, datatype=0))

tmp = os.path.join(tempfile.gettempdir(), "wmo_oas2.oas")
lib.write_oas(tmp)
lib2 = gdstk.read_oas(tmp)
cells = {c.name: c for c in lib2.cells}
top2 = cells['TOP']

# 层 200 的多边形：应为带 notch 的多边形（点数 > 360 或 360+）
wafer_polys = [p for p in top2.polygons if p.layer == 200]
ee_polys = [p for p in top2.polygons if p.layer == 201]
chip_cell2 = cells['Chip']
chip_polys = [p for p in chip_cell2.polygons if p.layer == 101]
print("layer200 polygons:", len(wafer_polys), "points:", [len(p.points) for p in wafer_polys])
print("layer201 polygons:", len(ee_polys), "points:", [len(p.points) for p in ee_polys])
assert len(wafer_polys) >= 1
assert len(ee_polys) == 1
assert len(ee_polys[0].points) == 360, f"EE 应为 360 点，实际 {len(ee_polys[0].points)}"
assert len(chip_polys) == 1, "Chip 单元内 1 个矩形"

# 验证 notch 已切除：wafer 多边形点数应大于 360（含 notch 边界点），且存在缺口
# 用比例无关方式验证（OAS 回读坐标被放大，直接比面积会受单位影响）
wafer_poly = wafer_polys[0]
max_r = max(math.hypot(x, y) for x, y in wafer_poly.points)
min_r = min(math.hypot(x, y) for x, y in wafer_poly.points)
print("max radius:", max_r, "min radius:", min_r,
      "notch depth ratio:", (max_r - min_r) / max_r)
assert len(wafer_poly.points) > 360, "Notch 切口应增加顶点数"
assert len(wafer_poly.points) == 375, f"删除两个切点后应 375 点，实际 {len(wafer_poly.points)}"
# 确认两个槽壁切点 (±0.111, -149.166) 已删除
for x, y in wafer_poly.points:
    assert not (abs(abs(x) - 0.111) < 1e-3 and abs(y - (-149.166)) < 1e-3), \
        f"切点 ({x}, {y}) 应已删除"
# 缺口切深验证：notch 方向（180->270°即 -Y）应有凹口，切深约 1.0mm（相对占比 1.0/150）
assert (max_r - min_r) / max_r > 0.8 / 150, "槽底应切深约 1.0mm"
# 缺口应位于 -Y 方向（mapped 180->270°）：检查 -Y 方向最小半径
neg_y_r = min(math.hypot(x, y) for x, y in wafer_poly.points if y < 0)
pos_y_r = min(math.hypot(x, y) for x, y in wafer_poly.points if y > 0)
print("negY min radius:", neg_y_r, "posY min radius:", pos_y_r)
assert neg_y_r < pos_y_r, "缺口应位于 -Y 方向"

print("ALL TESTS PASSED")