import urllib.request


def get(url):
    return urllib.request.urlopen(url, timeout=10).read().decode("utf-8")


html = get("http://127.0.0.1:8000/creators")
js = get("http://127.0.0.1:8000/static/js/app.js")
css = get("http://127.0.0.1:8000/static/css/style.css")

print("页面 copy-btn 次数:", html.count("copy-btn"))
print("页面 data-copy 次数:", html.count("data-copy="))
print("页面含'示例数据'标注:", "示例数据" in html)
print("JS 含 copyText:", "copyText" in js)
print("JS 含 .copy-btn 事件委托:", ".copy-btn" in js)
print("CSS 含 .copy-btn 样式:", ".copy-btn" in css)
