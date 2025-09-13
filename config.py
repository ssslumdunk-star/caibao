#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""配置文件 - 用于设置美股财报抓取工具的默认参数"""

# 默认股票代码列表（热门美股）
DEFAULT_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'BRK.A',
    'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'MRK', 'PEP', 'DIS', 'KO'
]

# 默认财报类型
# 10-K: 年报
# 10-Q: 季报
DEFAULT_FILING_TYPE = '10-K'

# 默认获取的年份数量
DEFAULT_YEARS = 5

# 请求超时设置（秒）
REQUEST_TIMEOUT = 30

# 随机延迟范围（秒）- 用于避免被封IP
MIN_DELAY = 1
MAX_DELAY = 3

# 重试次数设置
MAX_RETRIES = 3

# 数据存储设置
DATA_DIR = 'data'

# Excel文件格式设置
EXCEL_ENGINE = 'openpyxl'

# 日志设置
LOG_LEVEL = 'INFO'  # 可选值: DEBUG, INFO, WARNING, ERROR
LOG_FILE = 'us_stock_filing_scraper.log'

# 高级设置
# 是否显示详细的请求/响应信息
SHOW_VERBOSE_OUTPUT = False

# 自定义HTTP请求头
CUSTOM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive'
}