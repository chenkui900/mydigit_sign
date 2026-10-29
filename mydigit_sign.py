import os
import re
import time
import requests
from bs4 import BeautifulSoup
import http.cookiejar
from urllib.parse import urljoin

# ==================== 基础配置 ====================
COOKIE_FILE = "cookies.txt"
LOGIN_URL = "https://www.mydigit.cn"
SPACE_URL = "https://www.mydigit.cn"
SIGN_PAGE_URL = "https://www.mydigit.cn/k_misign-sign.html"

# (连接超时, 读取超时) 单位：秒
TIMEOUT = (15, 60)
# 网络请求重试次数与间隔（秒）
RETRY_TIMES = 3
RETRY_DELAY = 20

session = requests.Session()
session.trust_env = False
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.mydigit.cn',
})


def get_with_retry(url, **kwargs):
    """带重试的 GET 请求：网络超时/连接失败时最多重试 RETRY_TIMES 次。"""
    last_err = None
    for attempt in range(1, RETRY_TIMES + 1):
        try:
            return session.get(url, timeout=TIMEOUT, **kwargs)
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            last_err = e
            print(f"[警告] 第 {attempt}/{RETRY_TIMES} 次请求失败: "
                  f"{type(e).__name__}: {e}")
            if attempt < RETRY_TIMES:
                print(f"[提示] {RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
        except Exception as e:
            last_err = e
            print(f"[警告] 第 {attempt}/{RETRY_TIMES} 次请求异常: "
                  f"{type(e).__name__}: {e}")
            if attempt < RETRY_TIMES:
                time.sleep(RETRY_DELAY)
    raise last_err


def main():
    print("开始执行数码之家自动签到脚本...")

    # ---------- 1. 加载 Cookie ----------
    if not os.path.exists(COOKIE_FILE):
        print(f"[错误] 未找到 Cookie 文件，请确保 {COOKIE_FILE} 在同目录下。")
        return
    try:
        cookie_jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(cookie_jar)
        print("[提示] 成功从 cookies.txt 中载入凭证。")
    except Exception as e:
        print(f"[错误] 加载 Cookie 失败: {e}")
        return

    # ---------- 2. 检查登录状态（带重试） ----------
    try:
        res = get_with_retry(LOGIN_URL)
        if "logout" in res.text or "退出" in res.text:
            print("[成功] 账号登录状态有效！")
        else:
            print("[失败] 登录状态已失效，请重新从浏览器导出最新的 cookies.txt。")
            return
    except Exception as e:
        print(f"[错误] 重试 {RETRY_TIMES} 次后仍无法连接数码之家登录页: "
              f"{type(e).__name__}: {e}")
        return

    # ---------- 3. 签到（带重试） ----------
    try:
        sign_page_res = get_with_retry(SIGN_PAGE_URL)
        html = sign_page_res.text
        print(f"[调试] 签到页面状态码: {sign_page_res.status_code}, 长度: {len(html)}")

        # 优先正则匹配 operation=qiandao 的链接
        href = None
        m = re.search(r'(plugin\.php\?id=k_misign:sign[^"\'\s<>]*operation=qiandao[^"\'\s<>]*)', html)
        if m:
            href = m.group(1)
            print("[调试] 通过正则提取到签到链接")
        else:
            soup = BeautifulSoup(html, 'html.parser')
            tag = soup.find('a', id='JD_sign') or soup.find('a', href=re.compile('operation=qiandao'))
            if tag and tag.get('href'):
                href = tag['href']
                print("[调试] 通过标签提取到签到链接")

        # 备用：若没找到链接，则用 formhash 直接构造
        if not href:
            fm = re.search(r'name="formhash"\s+value="([^"]+)"', html)
            if not fm:
                fm = re.search(r'value="([^"]+)"\s+name="formhash"', html)
            if fm:
                formhash = fm.group(1)
                print(f"[调试] 未找到签到链接，改用 formhash 构造：{formhash}")
                href = (f"plugin.php?id=k_misign:sign&operation=qiandao"
                        f"&formhash={formhash}&format=empty&inajax=1")

        if not href:
            print("[提示] 未找到签到链接，页面片段如下：")
            print(html[:800])
        else:
            href = href.replace('&amp;', '&')
            actual_sign_url = urljoin(sign_page_res.url, href)
            print(f"[提示] 签到链接: {actual_sign_url}")

            sign_res = get_with_retry(
                actual_sign_url,
                headers={
                    'Referer': sign_page_res.url,
                    'X-Requested-With': 'XMLHttpRequest',
                },
            )
            text = sign_res.text or ""
            print(f"[调试] 签到响应状态码: {sign_res.status_code}")
            print(f"[调试] 签到响应内容: {text[:400]!r}")

            ok_words = ["签到成功", "已经签到", "已签到", "签到完成", "今日已签",
                        "CDATA[签到成功]", "CDATA[已经签到]",
                        "CDATA[您今天已经签到过了]"]
            if any(w in text for w in ok_words):
                print("[成功] 数码之家打卡签到成功（或今日已签到）！")
            elif "CDATA[]" in text or text.strip() == "":
                print("[提示] 服务器返回空内容，通常表示今日已签到。")
            else:
                print("[提示] 返回内容无法识别，请根据上方 [调试] 内容判断。")

    except Exception as e:
        print(f"[错误] 签到过程中发生异常（已重试 {RETRY_TIMES} 次）: "
              f"{type(e).__name__}: {e}")

    # ---------- 4. 每日活跃（带重试，失败不影响结果） ----------
    try:
        get_with_retry(SPACE_URL)
        print("[完成] 每日访问活跃任务已执行。")
    except Exception:
        print("[提示] 每日活跃访问失败（不影响签到结果）。")


if __name__ == "__main__":
    main()
