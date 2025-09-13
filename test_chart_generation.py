#!/usr/bin/env python3
import matplotlib
import matplotlib.pyplot as plt
import os

# 创建测试数据
years = [2021, 2022, 2023]
values = [15000000, 18000000, 16500000]

# 创建图表
plt.figure(figsize=(10, 6))
plt.plot(years, values, marker='o', linestyle='-', color='b')
plt.title('INTC Free Cash Flow Trend Test')
plt.xlabel('Year')
plt.ylabel('Free Cash Flow')
plt.grid(True)

# 添加数据标签
for i, v in enumerate(values):
    plt.text(years[i], v, f'${v:,.0f}', ha='center', va='bottom')

# 保存图表到当前目录
chart_path = 'test_chart.png'
plt.savefig(chart_path)
plt.close()

# 验证文件是否生成
if os.path.exists(chart_path):
    print(f"测试图表已成功生成: {os.path.abspath(chart_path)}")
    print(f"文件大小: {os.path.getsize(chart_path)} bytes")
else:
    print("错误: 测试图表生成失败")

# 打印系统信息
print(f"matplotlib版本: {matplotlib.__version__}")
print(f"当前工作目录: {os.getcwd()}")
print(f"是否有写入权限: {os.access('.', os.W_OK)}")