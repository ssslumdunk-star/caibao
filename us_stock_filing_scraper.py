#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import random
import logging
import sys
from config import (
    DEFAULT_TICKERS, DEFAULT_FILING_TYPE, DEFAULT_YEARS,
    REQUEST_TIMEOUT, MIN_DELAY, MAX_DELAY, MAX_RETRIES,
    DATA_DIR, EXCEL_ENGINE, LOG_LEVEL, LOG_FILE, SHOW_VERBOSE_OUTPUT,
    CUSTOM_HEADERS
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('USStockFilingScraper')

class USStockFilingScraper:
    def __init__(self):
        # 设置请求头，模拟浏览器访问
        self.headers = CUSTOM_HEADERS
        
        # 创建数据文件夹
        self.data_dir = DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 常用美股公司股票代码
        self.popular_stocks = DEFAULT_TICKERS
        
        # 初始化请求会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _make_request(self, url, method='get', **kwargs):
        """带重试机制的HTTP请求方法"""
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                # 添加随机延迟
                time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
                
                if method.lower() == 'get':
                    response = self.session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
                elif method.lower() == 'post':
                    response = self.session.post(url, timeout=REQUEST_TIMEOUT, **kwargs)
                else:
                    raise ValueError(f"不支持的请求方法: {method}")
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"请求失败 ({retry_count}/{MAX_RETRIES}): {str(e)}")
                
                if retry_count >= MAX_RETRIES:
                    logger.error(f"达到最大重试次数，请求失败: {url}")
                    raise
                
                # 指数退避策略
                wait_time = (2 ** retry_count) + random.uniform(0, 1)
                logger.info(f"{wait_time:.2f}秒后重试...")
                time.sleep(wait_time)
    
    def get_company_filings(self, ticker, filing_type=DEFAULT_FILING_TYPE, years=DEFAULT_YEARS):
        """
        获取公司的财报文件
        ticker: 股票代码
        filing_type: 财报类型，10-K是年报，10-Q是季报
        years: 获取最近几年的数据
        """
        logger.info(f"正在获取{ticker}的{filing_type}财报数据...")
        
        # 使用EDGAR数据库API获取财报信息
        base_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={filing_type}&count=100"
        
        try:
            response = self._make_request(base_url)
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 解析表格获取财报链接
            filings = []
            table = soup.find('table', class_='tableFile2')
            
            if not table:
                logger.warning(f"未找到{ticker}的{filing_type}财报数据")
                return None
            
            rows = table.find_all('tr')[1:]  # 跳过表头
            current_year = datetime.now().year
            target_years = range(current_year - years + 1, current_year + 1)
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 5:
                    continue
                
                filing_date = cols[3].text.strip()
                try:
                    filing_year = int(filing_date.split('-')[0])
                except (ValueError, IndexError):
                    logger.warning(f"无法解析财报日期: {filing_date}")
                    continue
                
                # 只获取目标年份的数据
                if filing_year not in target_years:
                    continue
                
                # 获取财报详情页链接
                filing_link_elem = cols[1].find('a', href=True)
                if not filing_link_elem:
                    logger.warning(f"未找到财报详情页链接")
                    continue
                
                filing_link = filing_link_elem['href']
                filing_detail_url = f"https://www.sec.gov{filing_link}"
                
                # 获取财报文档链接
                doc_url = self._get_filing_document_url(filing_detail_url)
                
                filings.append({
                    'ticker': ticker,
                    'filing_type': filing_type,
                    'filing_date': filing_date,
                    'year': filing_year,
                    'detail_url': filing_detail_url,
                    'doc_url': doc_url
                })
            
            if not filings:
                logger.warning(f"未找到{ticker}在目标年份内的{filing_type}财报数据")
                return None
            
            logger.info(f"成功获取到{ticker}的{len(filings)}份{filing_type}财报数据")
            return filings
            
        except Exception as e:
            logger.error(f"获取{ticker}的财报数据时出错: {str(e)}")
            return None
    
    def _get_filing_document_url(self, detail_url):
        """获取财报文档的实际链接"""
        try:
            response = self._make_request(detail_url)
            
            soup = BeautifulSoup(response.text, 'lxml')
            table = soup.find('table', class_='tableFile')
            
            if not table:
                logger.warning(f"未找到文档表格: {detail_url}")
                return None
            
            # 找到第一个文档链接（通常是主要财报文档）
            first_row = table.find('tr')
            if first_row:
                doc_link_elem = first_row.find('a', href=True)
                if doc_link_elem:
                    doc_link = doc_link_elem['href']
                    return f"https://www.sec.gov{doc_link}"
            
            logger.warning(f"未找到文档链接: {detail_url}")
            return None
            
        except Exception as e:
            logger.error(f"获取财报文档链接时出错: {str(e)}")
            return None
    
    def download_filing_document(self, filing_info):
        """下载财报文档"""
        try:
            if not filing_info.get('doc_url'):
                logger.warning("文档URL为空，跳过下载")
                return None
            
            ticker = filing_info['ticker']
            filing_type = filing_info['filing_type']
            filing_date = filing_info['filing_date']
            
            # 创建公司文件夹
            company_dir = os.path.join(self.data_dir, ticker)
            os.makedirs(company_dir, exist_ok=True)
            
            # 构造文件名
            file_name = f"{ticker}_{filing_type}_{filing_date}.html"
            file_path = os.path.join(company_dir, file_name)
            
            # 检查文件是否已存在
            if os.path.exists(file_path):
                logger.info(f"文件{file_name}已存在，跳过下载")
                return file_path
            
            logger.info(f"正在下载{file_name}...")
            response = self._make_request(filing_info['doc_url'])
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"成功下载到{file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"下载财报文档时出错: {str(e)}")
            return None
    
    def extract_financial_data(self, filing_file_path):
        """从财报文档中提取关键财务数据"""
        try:
            if not os.path.exists(filing_file_path):
                logger.warning(f"文件{filing_file_path}不存在")
                return None
            
            # 这里是简化版的财务数据提取逻辑
            # 实际应用中可能需要更复杂的解析逻辑
            with open(filing_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'lxml')
            
            # 提取公司名称和报告期
            company_name = "未知"
            report_period = "未知"
            
            # 尝试从文档中提取公司名称
            try:
                company_name_elem = soup.find('span', {'class': 'companyName'})
                if company_name_elem:
                    company_name = company_name_elem.text.strip().split('CIK#')[0].strip()
            except Exception:
                pass
            
            # 尝试从文档中提取报告期
            try:
                period_elem = soup.find(text=lambda text: text and 'period of report' in text.lower())
                if period_elem:
                    report_period = period_elem.find_next('div').text.strip() if period_elem.find_next('div') else report_period
            except Exception:
                pass
            
            # 尝试从文档中提取关键财务数据
            financial_data = {
                'revenue': None,
                'net_income': None,
                'total_assets': None,
                'total_liabilities': None,
                'eps': None,
                'free_cash_flow': None
            }
            
            # 这里仅作为示例，实际需要根据具体的财报结构进行调整
            # 在实际应用中，可能需要使用正则表达式或更复杂的解析方法
            text = soup.get_text().lower()
            
            # 简化版的关键词搜索
            if 'revenue' in text:
                # 使用正则表达式查找收入数值
                revenue_match = re.search(r'revenue.*?([\d,]+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
                financial_data['revenue'] = revenue_match.group(1).replace(',', '') if revenue_match else None
            
            if 'net income' in text:
                net_income_match = re.search(r'net income.*?([\d,]+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
                financial_data['net_income'] = net_income_match.group(1).replace(',', '') if net_income_match else None
            
            if 'total assets' in text:
                assets_match = re.search(r'total assets.*?([\d,]+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
                financial_data['total_assets'] = assets_match.group(1).replace(',', '') if assets_match else None
            
            if 'total liabilities' in text:
                liabilities_match = re.search(r'total liabilities.*?([\d,]+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
                financial_data['total_liabilities'] = liabilities_match.group(1).replace(',', '') if liabilities_match else None
            
            if 'earnings per share' in text or 'eps' in text:
                eps_match = re.search(r'earnings per share.*?([\d.]+)', text, re.IGNORECASE | re.DOTALL)
                financial_data['eps'] = eps_match.group(1) if eps_match else None
            
            if 'free cash flow' in text:
                fcf_match = re.search(r'free cash flow.*?([\d,]+\.?\d*)', text, re.IGNORECASE | re.DOTALL)
                financial_data['free_cash_flow'] = fcf_match.group(1).replace(',', '') if fcf_match else None
            
            logger.info(f"从{os.path.basename(filing_file_path)}中提取财务数据")
            return {
                'file_path': filing_file_path,
                'company_name': company_name,
                'report_period': report_period,
                'financial_data': financial_data
            }
            
        except Exception as e:
            logger.error(f"提取财务数据时出错: {str(e)}")
            return None
    
    def save_to_excel(self, data_list, output_file='financial_data.xlsx'):
        """将财务数据保存到Excel文件"""
        try:
            if not data_list:
                logger.warning("没有数据可保存")
                return False
            
            # 准备数据用于DataFrame
            rows = []
            for data in data_list:
                if 'financial_data' in data:
                    row = {
                        'ticker': data.get('ticker', ''),
                        'company_name': data.get('company_name', ''),
                        'report_period': data.get('report_period', ''),
                        'file_path': data.get('file_path', '')
                    }
                    row.update(data['financial_data'])
                    rows.append(row)
            
            if not rows:
                logger.warning("没有有效数据可保存")
                return False
            
            # 创建DataFrame并保存到Excel
            df = pd.DataFrame(rows)
            output_path = os.path.join(self.data_dir, output_file)
            
            # 保存到Excel，使用配置的引擎
            df.to_excel(output_path, index=False, engine=EXCEL_ENGINE)
            
            logger.info(f"财务数据已成功保存到{output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存数据到Excel时出错: {str(e)}")
            return False
    
    def run_for_multiple_stocks(self, tickers=None, filing_type=DEFAULT_FILING_TYPE, years=DEFAULT_YEARS):
        """为多个股票代码运行抓取任务"""
        if not tickers:
            tickers = self.popular_stocks
            logger.info(f"未提供股票代码列表，使用默认的热门股票列表（{len(tickers)}只股票）")
        
        all_financial_data = []
        total_success = 0
        total_failed = 0
        
        start_time = time.time()
        logger.info(f"开始抓取{len(tickers)}只股票的{filing_type}财报数据，时间范围：{years}年")
        
        for ticker in tickers:
            logger.info(f"\n===== 开始处理股票: {ticker} =====")
            
            try:
                # 获取财报信息
                filings = self.get_company_filings(ticker, filing_type, years)
                
                if not filings:
                    total_failed += 1
                    continue
                
                # 下载财报文档并提取数据
                for filing in filings:
                    try:
                        file_path = self.download_filing_document(filing)
                        
                        if file_path:
                            # 提取财务数据
                            financial_data = self.extract_financial_data(file_path)
                            
                            if financial_data:
                                financial_data['ticker'] = ticker
                                all_financial_data.append(financial_data)
                                total_success += 1
                    except Exception as e:
                        logger.error(f"处理{filing['filing_date']}的财报时出错: {str(e)}")
                        total_failed += 1
            except Exception as e:
                logger.error(f"处理股票{ticker}时出现未预期错误: {str(e)}")
                total_failed += 1
        
        # 保存所有数据到Excel
        if all_financial_data:
            self.save_to_excel(all_financial_data, f"financial_data_{filing_type}_{datetime.now().strftime('%Y%m%d')}.xlsx")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        logger.info(f"\n===== 任务完成 =====")
        logger.info(f"总耗时: {elapsed_time:.2f}秒")
        logger.info(f"成功处理: {total_success}份财报数据")
        logger.info(f"处理失败: {total_failed}份财报数据")
        logger.info(f"完成率: {total_success/(total_success+total_failed)*100:.2f}%" if (total_success+total_failed) > 0 else "无数据")


def main():
    """主函数，处理用户输入并启动抓取任务"""
    print("===== 美股财报自动抓取工具 =====")
    print("本工具将帮助您自动抓取美股上市公司的财报数据")
    
    try:
        scraper = USStockFilingScraper()
        
        # 让用户选择是使用默认股票列表还是自定义
        choice = input("\n请选择股票来源：1) 使用默认热门股票列表 2) 自定义股票代码 [默认: 1]: ") or '1'
        
        tickers = None
        if choice == '2':
            tickers_input = input("请输入股票代码，用逗号分隔（例如：AAPL,MSFT,GOOGL）: ")
            tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
            
            if not tickers:
                print("未输入有效股票代码，将使用默认列表")
                tickers = None
        
        # 让用户选择财报类型
        filing_choice = input("请选择财报类型：1) 年报(10-K) 2) 季报(10-Q) [默认: 1]: ") or '1'
        filing_type = '10-K' if filing_choice == '1' else '10-Q'
        
        # 让用户选择获取几年的数据
        years_input = input("请输入要获取的年份数量（例如：3）[默认: 5]: ") or '5'
        try:
            years = int(years_input)
            if years <= 0:
                raise ValueError("年份数量必须为正整数")
        except ValueError:
            years = DEFAULT_YEARS
            print(f"输入无效，使用默认值{years}年")
        
        # 开始运行
        print(f"\n即将开始抓取{years}年内的{filing_type}财报数据")
        print("注意：抓取过程中可能需要一定时间，请耐心等待...")
        scraper.run_for_multiple_stocks(tickers, filing_type, years)
        
        print("\n所有任务已完成，您可以在data文件夹中查看结果")
        
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        logger.error(f"程序运行出错: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()