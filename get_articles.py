import requests
import json
import time
import re
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def cache_get(cachefile):
    try:
        with open(cachefile, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def cache_set(cachefile, data):
    with open(cachefile, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def fetch60s(encode='json', offset=0, is_v1=False, force=False):
    api = 'https://www.zhihu.com/api/v4/columns/c_1715391799055720448/items?limit=8'
    today = time.strftime('%Y-%m-%d', time.gmtime(time.time() + 8 * 3600 - int(offset) * 24 * 3600))
    cachefile = f'60s_{today}.json'

    final_data = cache_get(cachefile)
    from_cache = final_data is not None and isinstance(final_data, dict) and 'result' in final_data
    new_data = None

    if not final_data or force:
        cookie = '__zse_ck=003_bnW9isRsE7j=GUdObPd7xeW3EOegV2wwAOwU=9x1xxsLiFCd+RTiESdH9SkbwcnH/hJvOlSgQyJPsnq/pzKC5kw4GjnYepAtr1Wm1uyb50xb; z_c0=2|1:0|10:1727679662|4:z_c0|92:Mi4xUnB2ZlZnQUFBQUFBQUpJMVRZRlFHU1lBQUFCZ0FsVk5ycHJuWndBTGZYaXNkZm9uUHV4TVUwRVJkS3cxMF9rZXpR|153bfe8d42e07be9b26d6067a7923aba29efbeb1a76b09a623e0d8a9d8e74540'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cookie': cookie
        }

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))

        response = session.get(api, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data and 'data' in data and isinstance(data['data'], list):
            reg = r'<p\s+data-pid=[^<>]+>([^<>]+)</p>'

            for item in data['data']:
                updated = item.get('updated', item.get('created', 0))
                day = time.strftime('%Y-%m-%d', time.gmtime(int(updated) + 8 * 3600))
                cachefile = f'60s_{day}.json'

                if item.get('content_need_truncated', False):
                    if cache_get(cachefile):
                        continue

                    article_response = session.get(item['url'], headers=headers)
                    article_response.raise_for_status()
                    article_html = article_response.text

                    match = re.search(r'<script id="js-initialData" type="text/json">(\{.+\})</script>', article_html)
                    if match:
                        init_data = json.loads(match.group(1))
                        c = init_data.get('initialState', {}).get('entities', {}).get('articles', {}).get(item['id'])
                        if c:
                            item = {**item, **c}
                            item['content_need_truncated'] = False

                    if item.get('content_need_truncated', False):
                        continue

                content = item.get('content', '')
                url = item.get('url', '')
                title_image = item.get('title_image', '')

                match = re.search(r'(\d{4}年.+星期.+农历[^<]+)', content)
                date = match.group(1) if match else ''

                matches = re.findall(reg, content)
                result = [re.sub(r'<[^<>]+>', '', e) for e in matches]

                if result:
                    f_data = {
                        'url': url,
                        'result': result,
                        'title_image': title_image,
                        'date': date,
                        'updated': updated * 1000,
                    }

                    cache_set(cachefile, f_data)

                    if today == day:
                        final_data = f_data
                    if not new_data:
                        new_data = f_data

    if not final_data:
        final_data = new_data or {}

    if is_v1:
        if encode == 'json':
            return {'result': final_data.get('result', [])}
        else:
            return '\n'.join(final_data.get('result', []))
    else:
        news = [re.sub(r'^(\d+)、\s*', r'\1. ', e) for e in final_data.get('result', [])]
        tip = news.pop() if news else ''

        if encode == 'json':
            return {
                'news': news,
                'tip': tip,
                'date': final_data.get('date', ''),
                'updated': final_data.get('updated', 0),
                'url': final_data.get('url', ''),
                'cover': final_data.get('title_image', ''),
                'fromCache': from_cache,
            }
        else:
            return '\n'.join(news + [tip])

# 测试
data = fetch60s(encode='json', offset=0, is_v1=False, force=True)
print(json.dumps(data, ensure_ascii=False, indent=4))