#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
美股财报抓取工具示例用法

这个脚本演示了如何使用USStockFilingScraper类来抓取单个股票的财报数据
"""

from us_stock_filing_scraper import USStockFilingScraper


def example_single_stock():
    """示例：抓取单个股票的财报数据"""
    print("===== 示例：抓取单个股票的财报数据 =====")
    
    # 创建抓取器实例
    scraper = USStockFilingScraper()
    
    # 选择一个股票代码，例如苹果公司(AAPL)
    ticker = 'AAPL'
    filing_type = '10-K'  # 年报
    years = 3  # 获取最近3年的数据
    
    print(f"\n1. 获取{ticker}的{filing_type}财报信息...")
    filings = scraper.get_company_filings(ticker, filing_type, years)
    
    if not filings:
        print("未找到财报信息")
        return
    
    print(f"找到{len(filings)}份财报")
    
    # 下载第一份财报文档
    print(f"\n2. 下载第一份财报文档 ({filings[0]['filing_date']})...")
    file_path = scraper.download_filing_document(filings[0])
    
    if not file_path:
        print("下载失败")
        return
    
    # 提取财务数据
    print(f"\n3. 从财报中提取财务数据...")
    financial_data = scraper.extract_financial_data(file_path)
    
    if financial_data:
        print(f"\n提取的财务数据：")
        print(f"公司名称: {financial_data['company_name']}")
        print(f"报告期: {financial_data['report_period']}")
        print("关键财务指标:")
        for key, value in financial_data['financial_data'].items():
            print(f"  {key}: {value}")
    
    print(f"\n示例完成！完整数据保存在: {file_path}")


def example_multiple_stocks():
    """示例：抓取多个股票的财报数据并保存到Excel"""
    print("\n===== 示例：抓取多个股票的财报数据并保存到Excel =====")
    
    # 创建抓取器实例
    scraper = USStockFilingScraper()
    
    # 选择几个股票代码进行演示
    tickers = ['AAPL', 'MSFT']  # 苹果和微软
    filing_type = '10-K'  # 年报
    years = 2  # 获取最近2年的数据
    
    print(f"开始抓取{len(tickers)}只股票的财报数据...")
    scraper.run_for_multiple_stocks(tickers, filing_type, years)
    
    print("\n示例完成！Excel数据文件已保存在data文件夹中")


if __name__ == "__main__":
    print("欢迎使用美股财报抓取工具示例脚本")
    print("此脚本将演示工具的基本功能")
    
    try:
        # 运行单个股票的示例
        example_single_stock()
        
        # 询问用户是否继续运行多个股票的示例
        choice = input("\n是否继续运行多个股票的示例？(y/n): ")
        if choice.lower() == 'y':
            example_multiple_stocks()
        
        print("\n所有示例运行完毕！")
        
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")