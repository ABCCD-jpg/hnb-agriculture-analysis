import sys
from pathlib import Path
# 当前文件core/gui.py，.parent=/core,.parent.parent= 项目根目录agri_price_spider
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import logging

from config import logger
from pipeline import run_pipeline

# 日志队列处理器
class QueueHandler(logging.Handler):
    def __init__(self, log_queue, text_widget):
        super().__init__()
        self.log_queue = log_queue
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        # 按日志级别区分颜色
        if record.levelno == logging.INFO:
            tag = "info"
        elif record.levelno == logging.WARNING:
            tag = "warn"
        elif record.levelno >= logging.ERROR:
            tag = "err"
        else:
            tag = "normal"
        self.log_queue.put((msg, tag))

class CrawlerApp:
    def __init__(self, root):
        self.root = root
        # 精简窗口标题 + 修复geometry格式（去掉逗号，使用x分隔）
        self.root.title("农产品行情采集分析系统")
        self.root.geometry("880x680")
        self.root.resizable(True, True)
        self.log_queue = queue.Queue()
        self.running = False
        self.create_widgets()
        self.setup_logging()
        self.update_log()

    def setup_logging(self):
        # 给日志文本添加颜色标签
        self.log_text.tag_config("info", foreground="#000000")
        self.log_text.tag_config("warn", foreground="#e67700")
        self.log_text.tag_config("err", foreground="#d62828")
        self.log_text.tag_config("normal", foreground="#333333")

        queue_handler = QueueHandler(self.log_queue, self.log_text)
        queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(queue_handler)

    def create_widgets(self):
        # 全局统一内边距
        pad_x = 12
        pad_y = 10

        # ========== 查询设置分区 ==========
        input_frame = ttk.LabelFrame(self.root, text="📌 查询设置")
        input_frame.pack(fill=tk.X, padx=18, pady=12)
        # 分区标题加粗
        style = ttk.Style()
        style.configure("TLabelframe.Label", font=("微软雅黑", 11, "bold"))

        # 品类输入行
        ttk.Label(input_frame, text="查询品类（英文逗号分隔）：", font=("微软雅黑", 10)).grid(
            row=0, column=0, padx=pad_x, pady=pad_y, sticky=tk.W
        )
        self.fruit_entry = ttk.Entry(input_frame, width=62, font=("微软雅黑", 10))
        self.fruit_entry.grid(row=0, column=1, padx=pad_x, pady=pad_y)
        # 灰色占位提示文字
        self.fruit_entry.insert(0, "例：榴莲,苹果,草莓,芒果")
        self.fruit_entry.bind("<FocusIn>", self.clear_entry_hint)

        # 页数输入行
        ttk.Label(input_frame, text="爬取最大页数：", font=("微软雅黑", 10)).grid(
            row=1, column=0, padx=pad_x, pady=pad_y, sticky=tk.W
        )
        self.page_entry = ttk.Entry(input_frame, width=12, font=("微软雅黑", 10))
        self.page_entry.grid(row=1, column=1, padx=pad_x, pady=pad_y, sticky=tk.W)
        self.page_entry.insert(0, "正整数")
        self.page_entry.bind("<FocusIn>", self.clear_page_hint)

        # 蓝色主按钮
        self.start_btn = tk.Button(
            input_frame, text="开始查询", command=self.start_crawl,
            bg="#0066CC", fg="white", font=("微软雅黑", 10, "bold"), width=14
        )
        self.start_btn.grid(row=0, column=2, rowspan=2, padx=25, pady=pad_y)

        # ========== 运行日志分区 ==========
        log_frame = ttk.LabelFrame(self.root, text="📋 运行日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=6)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=('微软雅黑', 9), bg='#f8f9fa'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ========== 底部状态栏 ==========
        self.status_var = tk.StringVar()
        self.status_var.set("🟢 准备就绪 | 所有结果保存至 assets/output")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var,
            anchor=tk.W, relief=tk.SUNKEN, padding=8, font=("微软雅黑", 9)
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # 输入框提示文字清除事件
    def clear_entry_hint(self, event):
        if self.fruit_entry.get() == "例：榴莲,苹果,草莓,芒果":
            self.fruit_entry.delete(0, tk.END)
    def clear_page_hint(self, event):
        if self.page_entry.get() == "正整数":
            self.page_entry.delete(0, tk.END)

    def update_log(self):
        while not self.log_queue.empty():
            msg, tag = self.log_queue.get()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + '\n', tag)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(100, self.update_log)

    def start_crawl(self):
        if self.running:
            messagebox.showwarning("提示", "任务正在运行中，请等待完成！")
            return
        fruits_str = self.fruit_entry.get().strip()
        # 过滤占位文字
        if fruits_str in ["", "例：榴莲,苹果,草莓,芒果"]:
            messagebox.showerror("错误", "请输入需要查询的品类！")
            return
        keywords = [f.strip() for f in fruits_str.split(',') if f.strip()]
        if not keywords:
            messagebox.showerror("错误", "品类请使用英文逗号分隔！")
            return
        page_text = self.page_entry.get().strip()
        if page_text in ["", "正整数"]:
            messagebox.showerror("错误", "请填写爬取页数！")
            return
        try:
            max_page = int(page_text)
            if max_page < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "页数必须为大于0的整数！")
            return
        confirm_text = f"即将采集品类：\n{', '.join(keywords)}\n\n最大爬取页数：{max_page}"
        confirm = messagebox.askyesno("确认开始", confirm_text)
        if not confirm:
            return
        self.running = True
        self.start_btn.config(state=tk.DISABLED, bg="#80a8d8")
        self.status_var.set("🟡 任务运行中，请稍候...")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.run_task, args=(keywords, max_page))
        thread.daemon = True
        thread.start()

    def run_task(self, keywords, max_page):
        """执行任务（调用pipeline）"""
        try:
            # 调用统一的pipeline
            result = run_pipeline(keywords, max_page)

            # 根据结果更新GUI
            self.root.after(0, self._on_task_complete, result)

        except Exception as e:
            logger.error(f"任务异常：{str(e)}", exc_info=True)
            self.root.after(0, self._on_task_error, str(e))

    def _on_task_complete(self, result):
        """任务完成回调"""
        self.running = False
        self.start_btn.config(state=tk.NORMAL, bg="#0066CC")

        if result['success']:
            self.status_var.set(f"✅ 任务完成，共 {result['total_records']} 条数据")

            # 构建提示信息
            msg = f"数据采集与分析完成！\n\n"
            msg += f"有效数据：{result['total_records']} 条\n"
            msg += f"报告路径：{result['report_path']}\n"

            if result['failed_categories']:
                msg += f"\n注意：以下品类失败：{', '.join(result['failed_categories'])}"

            messagebox.showinfo("任务完成", msg)
        else:
            self.status_var.set("🔴 任务失败")
            messagebox.showerror("任务失败", result['error_message'])