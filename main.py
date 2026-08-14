# main.py
import sys
from pathlib import Path

# 拿到项目根目录（main.py所在文件夹）
project_root = Path(__file__).parent
# 添加到系统检索路径，才能识别core文件夹
sys.path.insert(0, str(project_root))

# gui在core文件夹内，类名是你原来的 CrawlerApp
from core.gui import CrawlerApp

if __name__ == '__main__':
    import tkinter as tk
    root = tk.Tk()
    app = CrawlerApp(root)
    root.mainloop()