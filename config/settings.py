import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

# 1.最先加载环境变量，放在文件最上方！
load_dotenv()

# 2.从.env读取敏感配置，设置默认兜底值
LOGIN_COOKIE = os.getenv("LOGIN_COOKIE", "")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# 反爬配置，后面优化反爬会用到
# UA池
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36"
]
# 随机延时范围 秒
MIN_DELAY = 1
MAX_DELAY = 5
# 跨品类大延时
CATEGORY_SLEEP_MIN = 20
CATEGORY_SLEEP_MAX = 35
# 请求超时
TIMEOUT = 10
# 最大重试次数
MAX_RETRY = 3

# ========== 1. 文件路径配置 ==========
OUTPUT_DIR = 'assets/output'
# 消除竞争条件，移除if判断
# 使用exist_ok=True避免并发场景文件夹创建产生竞争条件
SAVE_PATH = 'assets/output/惠农网农产品行情数据.csv'
EXCEL_REPORT_PATH = 'assets/output/农产品价格分析报告.xlsx'
LOG_PATH = 'assets/output/项目运行日志.log'
DEBUG = True

# 确保输出目录存在（使用绝对路径）
from pathlib import Path
_BASE_DIR = Path(__file__).parent.parent
_OUTPUT_DIR_ABS = _BASE_DIR / OUTPUT_DIR
_OUTPUT_DIR_ABS.mkdir(parents=True, exist_ok=True)

# ========== 2. 爬虫固定配置 ==========
HANGQING_HOME = 'https://www.cnhnb.com/hangqing/'

# ========== 3. 省份常量列表 ==========
PROVINCE_LIST = [
    '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
    '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
    '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
    '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆'
]

# ========== 4. Matplotlib全局字体配置 ==========
import matplotlib.pyplot as plt
import seaborn as sns
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

# ========== 5. MongoDB全局连接（统一管理，不用每个文件重复创建） ==========
def get_mongo_collection():
    from pymongo import MongoClient
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client['hnb_agriculture']
        return db['price_data']
    except Exception as e:
        logger.error("MongoDB连接失败，请确认数据库已启动",exc_info=True)
        return None

# ========== 6. 全局日志对象（所有模块共用同一个logger，统一输出文件+控制台） ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(_BASE_DIR / LOG_PATH, encoding='utf-8'), logging.StreamHandler()]
    )
logger = logging.getLogger(__name__)
logging.getLogger("jieba").setLevel(logging.WARNING)

# ========== 7. 词云库可用性标记 ==========
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False
    logger.warning("wordcloud库未安装，词云功能将被跳过。请执行: pip install wordcloud")