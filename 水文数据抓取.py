import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os

# 输出文件夹
desktop = os.path.join(os.path.expanduser("~"), "Desktop")
output_folder = os.path.join(desktop, "河道数据汇总")
os.makedirs(output_folder, exist_ok=True)  # 文件夹不存在就创建

# URL
URL = "http://124.227.12.36:8259/sssq/hdsq/ShowRiverData.aspx"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

all_rows = []
columns = []

def get_form_data(soup):
    data = {}
    for inp in soup.find_all("input", type="hidden"):
        name = inp.get("name")
        if name:
            data[name] = inp.get("value", "")
    return data

def find_data_table(soup):
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        counts = [len(tr.find_all("td")) for tr in rows[:5] if tr.find_all("td")]
        if counts and len(set(counts)) == 1:
            return table
    return None

def parse_table(table, is_first_page=False):
    rows = table.find_all("tr")
    headers = []
    if is_first_page:
        headers = [cell.get_text(strip=True) for cell in rows[0].find_all(["th", "td"])]
    data = []
    for idx, tr in enumerate(rows):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cells or all(c == "" for c in cells):
            continue
        if is_first_page and idx == 0:
            continue
        data.append(cells)
    return headers, data

# ===== 第 1 页 =====
resp = session.get(URL)
resp.encoding = "utf-8"
soup = BeautifulSoup(resp.text, "html.parser")
form_data = get_form_data(soup)

# 总页数
hid_page = soup.find("input", {"id": "hidPageNum"})
if hid_page is None:
    raise RuntimeError("未能读取总页数 hidPageNum")
total_pages = int(hid_page["value"])
print(f"检测到总页数：{total_pages}")

# 解析第一页表格
table = find_data_table(soup)
if table is None:
    raise RuntimeError("未找到数据表格")
columns, page_data = parse_table(table, is_first_page=True)
all_rows.extend(page_data)

# ===== 翻页 =====
for page in range(2, total_pages + 1):
    print(f"正在抓取第 {page} 页")
    form_data["txtNowPage"] = str(page)
    form_data["__EVENTTARGET"] = "imgGo"
    form_data["__EVENTARGUMENT"] = ""
    resp = session.post(URL, data=form_data)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    form_data = get_form_data(soup)
    table = find_data_table(soup)
    if table:
        _, page_data = parse_table(table, is_first_page=False)
        all_rows.extend(page_data)

# ===== 导出 CSV =====
df = pd.DataFrame(all_rows, columns=columns)
now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_file = os.path.join(output_folder, f"河道数据汇总_{now_str}.csv")
df.to_csv(output_file, index=False, encoding="utf-8-sig")

print("="*50)
print(f"抓取完成：共抓取 {len(df)} 条记录")
print(f"CSV 文件已生成：{output_file}")
print("="*50)
