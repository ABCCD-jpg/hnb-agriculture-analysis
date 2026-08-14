import time
import re
import math
import random
from playwright.sync_api import sync_playwright
from config import logger, LOGIN_COOKIE, HANGQING_HOME, DEBUG
from utils.data_tools import clean_change, clean_price, extract_province

# 爬虫爬网页时，判断页面是否弹出登录拦截弹窗
def check_login_modal(page) -> bool:
    try:
        modal = page.locator('.el-dialog__wrapper')
        if modal.is_visible(timeout=800):
            modal_text = modal.inner_text(timeout=500)
            if '请登录' in modal_text or '继续浏览' in modal_text:
                return True
        return False
    except:
        return False

def crawl_category(keyword: str, max_page: int) -> list[dict]:
    result = []
    logger.info(f"===== 开始爬取品类：{keyword} =====")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=not DEBUG,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                viewport={'width': 1366, 'height': 768}
            )
            cookies = []
            for item in LOGIN_COOKIE.split(';'):
                if '=' in item:
                    name, value = item.strip().split('=', 1)
                    cookies.append({'name': name.strip(), 'value': value.strip(), 'domain': '.cnhnb.com', 'path': '/'})
            context.add_cookies(cookies)

            #打开首页
            page = context.new_page()
            page.goto(HANGQING_HOME, wait_until='domcontentloaded', timeout=30000)
            time.sleep(random.uniform(1.5, 2.5))
            # 记录搜索前第一条数据
            first_item_before = None
            try:
                first_before = page.locator('li.market-list-item').first
                if first_before.is_visible(timeout=1000):
                    first_item_before = first_before.inner_text().strip()
            except:
                pass

            # 搜索
            search_input = page.locator('input.search-ctn')
            search_input.click()
            search_input.fill('')
            time.sleep(0.3)
            for char in keyword:
                search_input.type(char, delay=random.randint(80, 200))
            time.sleep(0.5)
            page.keyboard.press('Enter')
            time.sleep(0.5)
            page.locator('div.s-r').click()
            logger.info(f"已搜索关键词：{keyword}")

            # 等待加载
            try:
                page.wait_for_selector('li.market-list-item, .empty-page, .no-data, .el-empty', timeout=8000)
                page.wait_for_load_state('networkidle', timeout=5000)
            except Exception as e:
                logger.warning(f"{keyword} 页面加载异常：{str(e)[:50]}")
                return result

            # 空状态检测
            empty_selectors = ['.empty-page', '.no-data', '.el-empty']
            if any(page.locator(sel).is_visible(timeout=300) for sel in empty_selectors):
                logger.info(f"关键词 {keyword} 无搜索结果，退出爬取")
                return result

            # 检测内容是否变化
            first_item_after = None
            try:
                first_after = page.locator('li.market-list-item').first
                if first_after.is_visible(timeout=1000):
                    first_item_after = first_after.inner_text().strip()
            except:
                pass

            #前后都有商品，单页面没刷新，搜索失效
            if first_item_before and first_item_after and first_item_before == first_item_after:
                logger.warning(f"搜索后列表内容未变化，可能搜索失败或无结果，放弃该品类")
                return result
            #无空白提示，但页面完全没有商品li标签，兜底拦截
            elif not first_item_after:
                logger.warning(f"搜索后未检测到列表项，放弃该品类")
                return result

            # 获取总页数
            try:
                total_text = page.locator('span.eye-pagination__total').inner_text(timeout=2000)
                total_match = re.search(r'共\s*(\d+)\s*条', total_text)
                total_count = int(total_match.group(1)) if total_match else 0
                total_page = math.ceil(total_count / 15) if total_count else 1
                actual_page = min(max_page, total_page)
                logger.info(f"总条数：{total_count} 条，总页数：{total_page} 页，本次爬取前 {actual_page} 页")
            except Exception as e:
                logger.warning(f"获取总页数失败：{str(e)[:50]}，按最大页数 {max_page} 爬取")
                actual_page = max_page

            last_flag = ''
            for page_num in range(1, actual_page + 1):
                logger.info(f"正在爬取第 {page_num} 页...")
                page_data = []
                for retry in range(3):
                    try:
                        page.wait_for_selector('li.market-list-item', timeout=3000)
                    except:
                        pass
                    try:
                        page_data = page.evaluate('''
                            () => {
                                const items = document.querySelectorAll('li.market-list-item');
                                const list = [];
                                items.forEach(li => {
                                    const texts = li.innerText.split('\\n').filter(t => t.trim());
                                    if (texts.length >= 4) {
                                        list.push({
                                            date: texts[0].trim(),
                                            name: texts[1].trim(),
                                            origin: texts[2].trim(),
                                            price: texts[3].trim(),
                                            change: texts[4] ? texts[4].trim() : '-'
                                        });
                                    }
                                });
                                return list;
                            }
                        ''')
                    except Exception as e:
                        logger.debug(f"第 {retry+1} 次提取失败：{str(e)[:50]}")
                    if page_data:
                        break
                    logger.info(f"第 {retry+1} 次提取为空，等待重试...")
                    time.sleep(1.5)

                if not page_data and check_login_modal(page):
                    logger.warning("检测到强制登录弹窗，终止爬取")
                    break
                if not page_data:
                    logger.info("多次重试无数据，已到达最后一页或无结果")
                    break
                current_flag = page_data[0]['name'] + page_data[0]['origin']
                if current_flag == last_flag:
                    logger.info("检测到重复内容，已到达最后一页")
                    break
                last_flag = current_flag

                for row in page_data:
                    cleaned_price = clean_price(row['price'])
                    if cleaned_price is None:
                        continue
                    result.append({
                        '品类': keyword,
                        '产品名称': row['name'],
                        '产地': row['origin'],
                        '省份': extract_province(row['origin']),
                        '原始价格文本': row['price'],
                        '价格(元/斤)': cleaned_price,
                        '涨跌幅(%)': clean_change(row['change']),
                        '发布日期': row['date']
                    })
                logger.info(f"本页提取 {len(page_data)} 条数据")

                # 翻页逻辑不变
                if page_num < actual_page:
                    next_btn = page.locator('button.btn-next').first
                    try:
                        btn_visible = next_btn.is_visible(timeout=1000)
                        btn_disabled = next_btn.is_disabled(timeout=1000)
                    except:
                        btn_visible = False
                        btn_disabled = True
                    if not btn_visible or btn_disabled:
                        logger.info("下一页按钮不可用，尝试跳转页码...")
                        try:
                            jump_input = page.locator('.eye-pagination__jump input')
                            jump_input.click()
                            jump_input.fill(str(page_num + 1))
                            page.locator('.eye-pagination__jump .btn-confirm').click()
                            time.sleep(random.uniform(2.5, 4))
                        except Exception as e:
                            logger.warning(f"跳转失败：{str(e)[:50]}，终止翻页")
                            break
                    else:
                        prev_flag = current_flag
                        try:
                            next_btn.click()
                            for _ in range(10):
                                time.sleep(0.5)
                                try:
                                    first_item = page.locator('li.market-list-item').first
                                    first_text = first_item.inner_text(timeout=500)
                                    if prev_flag not in first_text:
                                        break
                                except:
                                    pass
                            time.sleep(random.uniform(1, 2))
                        except Exception as e:
                            logger.warning(f"点击下一页失败：{str(e)[:50]}，尝试跳转")
                            try:
                                jump_input = page.locator('.eye-pagination__jump input')
                                jump_input.click()
                                jump_input.fill(str(page_num + 1))
                                page.locator('.eye-pagination__jump .btn-confirm').click()
                                time.sleep(random.uniform(2.5, 4))
                            except:
                                logger.error("翻页全部失败，终止当前品类")
                                break

            browser.close()
            logger.info(f"{keyword} 爬取完成，共获取 {len(result)} 条有效数据")
            return result

    except Exception as e:
        logger.error(f"爬取 {keyword} 失败：{str(e)}", exc_info=True)
        return result