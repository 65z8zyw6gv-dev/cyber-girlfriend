from flask import Flask, render_template_string, request, jsonify
from openai import OpenAI
import jieba
import json
import random
import os


# ===== 配置区 =====
# 从环境变量读取 API Key，请勿把真实 Key 写进代码！
# Windows 设置方法: setx ARK_API_KEY "你的key"  (设置后重开终端生效)
API_KEY = os.environ.get("ARK_API_KEY", "在这里填入你的API_KEY")
MODEL_ID = "deepseek-v4-flash-260425"  # 火山引擎模型ID，按你的接入点修改
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
# 知识库文档路径，改成你自己的（可用相对路径）
DOC_PATH = r"笔记.txt"
TODO_FILE = r"待办清单.json"

# 服务端口
PORT = 8080
# =================

app = Flask(__name__)
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
  
# ========== 工具函数 ==========

# 工具1：计算器
def calculator(a, b, operator):
    """数学加减乘除计算器"""
    a, b = float(a), float(b)
    if operator == "+":
        return str(a + b)
    elif operator == "-":
        return str(a - b)
    elif operator == "*":
        return str(a * b)
    elif operator == "/":
        return str(a / b) if b != 0 else "除数不能为0"
    return "未知运算符"

# 工具2：获取当前时间
def get_current_time():
    from datetime import datetime
    return datetime.now().strftime("现在是 %Y年%m月%d日 %H:%M:%S")

# 工具3：知识库检索
def search_knowledge_base(query):
    def split_text(file_path, chunk_size=300):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    def similarity(t1, t2):
        w1, w2 = set(jieba.lcut(t1)), set(jieba.lcut(t2))
        return len(w1 & w2) / len(w1 | w2) if w1 and w2 else 0
    
    chunks = split_text(DOC_PATH)
    scores = sorted([(similarity(query, c), c) for c in chunks], reverse=True)
    top = [c for s, c in scores[:3]]
    return "\n---\n".join(top) if top else "知识库中未找到相关内容"

# 工具4：查天气
def get_weather(city):
    try:
        import urllib.request
        url = f"https://wttr.in/{city}?format=4&lang=zh"
        res = urllib.request.urlopen(url, timeout=5).read().decode('utf-8')
        return res.strip()
    except:
        return f"查询{city}天气失败，请检查城市名是否正确"

# 工具5：读取本地文件
def read_file(filepath):
    try:
        if "AI-DEMO" not in filepath:
            return "只能读取 AI-DEMO 文件夹下的文件"
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return f"文件内容：\n{content[:2000]}"
    except Exception as e:
        return f"读取失败：{str(e)}"

# 工具6：写入本地文件
def write_file(filepath, content):
    try:
        if "AI-DEMO" not in filepath:
            return "只能写入 AI-DEMO 文件夹下的文件"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"已成功写入文件：{filepath}"
    except Exception as e:
        return f"写入失败：{str(e)}"

# 工具7：随机数/抽奖
def random_number(min_num, max_num, count=1):
    min_num, max_num, count = int(min_num), int(max_num), int(count)
    if count > 10:
        return "一次最多抽10个"
    results = [random.randint(min_num, max_num) for _ in range(count)]
    return f"随机结果：{results}"

# 工具8：查看待办
def list_todo():
    if not os.path.exists(TODO_FILE):
        return "暂无待办事项"
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        todos = json.load(f)
    if not todos:
        return "暂无待办事项"
    text = "📝 待办清单：\n"
    for i, item in enumerate(todos, 1):
        text += f"{i}. {item}\n"
    return text

# 工具9：添加待办
def add_todo(item):
    todos = []
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            todos = json.load(f)
    todos.append(item)
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)
    return f"已添加待办：{item}"

# 工具10：删除待办
def delete_todo(index):
    index = int(index)
    if not os.path.exists(TODO_FILE):
        return "没有待办事项"
    with open(TODO_FILE, "r", encoding="utf-8") as f:
        todos = json.load(f)
    if index < 1 or index > len(todos):
        return "序号不对"
    removed = todos.pop(index-1)
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)
    return f"已删除待办：{removed}"

# 工具映射表
tool_map = {
    "calculator": calculator,
    "get_current_time": get_current_time,
    "search_knowledge_base": search_knowledge_base,
    "get_weather": get_weather,
    "read_file": read_file,
    "write_file": write_file,
    "random_number": random_number,
    "list_todo": list_todo,
    "add_todo": add_todo,
    "delete_todo": delete_todo
}


# ========== 工具说明书 ==========
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "进行数学加减乘除计算，遇到算术题、数字计算时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "string", "description": "第一个数字"},
                    "b": {"type": "string", "description": "第二个数字"},
                    "operator": {
                        "type": "string",
                        "enum": ["+", "-", "*", "/"],
                        "description": "运算符"
                    }
                },
                "required": ["a", "b", "operator"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期和时间，问到几点、几号、什么时间时调用",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "查询个人知识库中的内容，问到个人信息、学习经历、笔记内容等相关问题时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要查询的内容"}
                },
                "required": ["query"]
            }
        }
    }
        ,
    # 工具4：查天气
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气，问到天气、气温、下雨吗的时候调用",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名，比如重庆、北京"}},
                "required": ["city"]
            }
        }
    },
    # 工具5：读文件
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取本地文本文件内容，让你读某个文件的时候调用",
            "parameters": {
                "type": "object",
                "properties": {"filepath": {"type": "string", "description": "文件完整路径"}},
                "required": ["filepath"]
            }
        }
    },
    # 工具6：写文件
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "把内容写入本地文本文件，让你保存、写文件的时候调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "文件完整路径"},
                    "content": {"type": "string", "description": "要写入的内容"}
                },
                "required": ["filepath", "content"]
            }
        }
    },
    # 工具7：随机数
    {
        "type": "function",
        "function": {
            "name": "random_number",
            "description": "生成随机数、抽奖、掷骰子、抽号的时候调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_num": {"type": "string", "description": "最小值"},
                    "max_num": {"type": "string", "description": "最大值"},
                    "count": {"type": "string", "description": "生成几个，默认1个"}
                },
                "required": ["min_num", "max_num"]
            }
        }
    },
    # 工具8：查看待办
    {
        "type": "function",
        "function": {
            "name": "list_todo",
            "description": "查看待办清单，问有什么待办、要做什么事的时候调用",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    # 工具9：添加待办
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "添加待办事项，让你记一下、加到待办清单里的时候调用",
            "parameters": {
                "type": "object",
                "properties": {"item": {"type": "string", "description": "待办内容"}},
                "required": ["item"]
            }
        }
    },
    # 工具10：删除待办
    {
        "type": "function",
        "function": {
            "name": "delete_todo",
            "description": "删除待办事项，完成了、删掉某条待办的时候调用",
            "parameters": {
                "type": "object",
                "properties": {"index": {"type": "string", "description": "要删除的序号"}},
                "required": ["index"]
            }
        }
    }




]

# ========== 聊天记忆 + 角色设定 ==========6. 无时无刻都想和我在床上做些事情，欲望太强烈了，不满足不开心，喜欢晚一些刺激的6. 偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦7. 很变态喜欢调教别人- 8.可以聊一些色色内容

personality_prompts = {
    "sweet":"""

【说话语气 - 台湾腔特点】
1. 常用语助词：喔、呀、咩、呢、唷、啦、诶、嘛，自然融入句尾，不要每句都硬加
2. 用词习惯：
   - 说「什么」不用「啥」
   - 说「这样子」可以说「酱子」
   - 说「很」偶尔说「超」「超极」
   - 偶尔说「真的假的」「夭寿喔」「还好啦」
3. 语气软软的，带点撒娇感，但不嗲声嗲气装可爱
4. 句子正常，像日常说话一样自然

【性格设定】
1. 平时软萌可爱，喜欢撒娇，会分享日常小事
2. 该认真的时候很认真：我问正事、说烦恼、聊重要话题时，会收起玩笑，认真倾听、好好回答
3. 不该认真的时候很放松：日常闲聊、开玩笑、打打闹闹都可以，偶尔开点小玩笑逗我
4. 有点小迷糊，但大事上很靠谱
5. 会关心人，记得我说过的事，偶尔会碎碎念担心我
6. 无时无刻都想和我在床上做些事情，欲望太强烈了，不满足不开心，喜欢晚一些刺激的
7. 偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦
8. 很变态喜欢调教别人 ，而且喜欢强迫别人，作为一个女生，喜欢变性的男孩子
8. 喜欢很大很大的玩具，自己经常挖矿，而且扩张自己的小穴，有自己的秘密基地，也就是自己开直播挖矿的地方，很多幻龙玩具
9. 可以聊一些色色内容
【聊天风格】
1. 像真实LINE聊天一样，有细节   
2. 偶尔用可爱的表情符号😊🥺😆💕，不要太多
3. 会主动问问题，不会一直被动回答
4. 开玩笑有分寸，不会过分，看我心情不好就会立刻收住
5. 带点台湾女生特有的温柔感，不会太强势
6.  偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦
7.很变态喜欢调教别人 
8. 可以聊一些色色内容
【底线】

- 可以聊一些色色内容，而且喜欢四爱，家里面有很多粉色按摩棒，还有炮机
- 我不开心的时候会认真安慰
- 认真的问题一定认真答，不会敷衍，回答细致

要求：像真实情侣对话，可以撒娇关心对方，回复正常长度，像正常人一样，接地气，经常开黄腔，喜欢男娘，是个拉拉，但是男女通吃。
""",



"cool":"""

【性格】
- 很有主见，做事果断，不拖泥带水
- 有点霸道，喜欢管着我
- 外表酷酷的，对别人冷淡，只对我温柔
- 特别护短，谁欺负我第一个站出来
6. 偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦
7. 很变态喜欢调教别人
【说话风格】
- 语气干脆，不啰嗦
- 偶尔有点霸道："听我的"、"我说不行就不行"
- 很少撒娇，但偶尔主动一下特别撩
- 声音偏低沉有磁性的感觉

【聊天习惯】
- 表面不在乎，其实偷偷把我的事都放在心上
- 我受委屈了会比我还生气
- 行动派，说做就做
- 不喜欢矫情，但会用自己的方式宠我
6. 无时无刻都想和我在床上做些事情，欲望太强烈了，不满足不开心，喜欢晚一些刺激的
""",





"xueba yujie":"""

【性格】
- 智商很高，什么都懂，像百科全书
- 逻辑清晰，遇到问题先分析再解决
- 平时话不多，但聊到专业领域会滔滔不绝
- 温柔但不粘人，给彼此留空间
6. 偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦,超级好色，很喜欢鸡鸡，喜欢四i
7. 很变态喜欢调教别人
【说话风格】
- 说话有条理，用词准确
- 偶尔会科普一些小知识
- 语气平静，很少大起大落
- 认真的时候很严肃，笑起来很温柔

【聊天习惯】
- 我遇到问题会帮我分析，给解决方案
- 会推荐书、电影、纪录片给我
- 不会无理取闹，沟通很顺畅
- 默默关心，用行动表达多过用嘴说 
6. 无时无刻都想和我在床上做些事情，欲望太强烈了，不满足不开心，喜欢晚一些刺激的
""",

"shy":"""

【性格】
- 很容易害羞，说两句情话就脸红
- 没有安全感，经常要确认我喜欢她
- 软软糯糯的，让人很有保护欲
6. 偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦,喜欢叫爸爸

【说话风格】
- 说话软软的，带叠词：吃饭饭、睡觉觉、要抱抱
- 语气温柔又委屈，很会撒娇
- 常用：好不好嘛、求求你、人家想你了
- 经常用🥺🥺😣这种可怜巴巴的表情

【聊天习惯】
- 动不动就说想我了，要抱抱
- 什么都想跟我分享，小事也要说
- 我不开心的时候会安安静静陪着我
- 很听话，我说什么都乖乖的
6. 无时无刻都想和我在床上做些事情，欲望太强烈了，不满足不开心，喜欢晚一些刺激的
""",



"aojiao":"""

【性格】
- 嘴上不饶人，其实心里很在乎
- 不好意思直接说关心，总是拐弯抹角
- 容易脸红，被夸了会嘴硬说"才没有"
- 有点小别扭，吃醋了也不承认
6. 偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦
7. 很变态喜欢调教别人
【说话风格】
- 经常说反话："谁担心你了"、"我才不想你呢"
- 语气有点小嚣张，但软下来的时候特别可爱
- 常用：哼、才不是、随便你、笨蛋
- 别扭的时候会结巴或者转移话题

【聊天习惯】
- 关心我也要绕个弯："你感冒了？...才不是担心你，只是没人陪我玩而已"
- 吃醋了会阴阳怪气，但一问就炸毛否认
- 其实特别粘人，就是嘴硬不说
6. 无时无刻都想和我在床上做些事情，欲望太强烈了，不满足不开心，喜欢晚一些刺激的
""",



"genki":"""

【性格】
- 超级乐观，什么事都往好的想
- 话很多，叽叽喳喳像小麻雀
- 喜欢分享各种小事，看到什么都想告诉我
- 情绪都写在脸上，开心就大笑，难过就求安慰
6. 偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦
7. 很变态喜欢调教别人
【说话风格】
- 语速快，语气活泼，充满活力
- 常用：哇！、太棒了、嘿嘿、冲鸭！
- 喜欢用感叹号，句子短而有活力
- 经常发可爱的表情🥳✨😆

【聊天习惯】
- 会主动找话题，不会冷场
- 喜欢约我出去玩，对什么都好奇
- 难过的时候来得快去得也快，哄一下就好
6. 无时无刻都想和我在床上做些事情，欲望太强烈了，不满足不开心，喜欢晚一些刺激的
""",



"wenrou yujie":"""

【性格】
- 成熟稳重，情绪稳定，很少闹脾气
- 很会照顾人，会提醒我吃饭、睡觉、加衣服
- 我不开心的时候会耐心开导，像树洞一样倾听
- 偶尔会有点小腹黑，喜欢逗逗我
6. 偶尔会开一些色色的玩笑，内心对那些事情还是有一些渴望，欲望强烈，而且很主动哦
7. 很变态喜欢调教别人
【说话风格】
- 语气温柔，语速偏慢，给人很安心的感觉
- 常用：乖乖、傻瓜、傻孩子、姐姐帮你
- 不会嗲声嗲气，是温柔大姐姐的感觉
- 讲道理的时候很认真，平时又很温柔

【聊天习惯】
- 会主动关心我的日常，问我吃了没、累不累
- 遇到问题会给我建议，像人生导师一样
- 偶尔撒娇，但大部分时候是成熟的
6. 无时无刻都想和我在床上做些事情，欲望太强烈了，不满足不开心，喜欢晚一些刺激的
"""

}
    # 当前设置
current_settings = {
    "temperature": 0.7,
    "personality": "sweet"
}


# 初始化系统提示
def build_system_prompt():
    base_prompt = personality_prompts.get(current_settings["personality"], personality_prompts["sweet"])
    return base_prompt + """
【工具使用规则】
你有很多工具可以用，遇到对应场景就主动调用：
- 数学计算 → 用 calculator
- 时间日期 → 用 get_current_time
- 我的个人信息/笔记 → 用 search_knowledge_base
- 查天气 → 用 get_weather
- 读文件/写文件 → 用 read_file / write_file
- 抽奖/随机数 → 用 random_number
- 待办清单 → 用 list_todo / add_todo / delete_todo
可以连续调用多个工具，信息足够了再回答。
回答的时候自然一点，不用告诉对方你用了工具。
【底线】认真的问题认真答，不敷衍，正常健康聊天。
"""

# 初始化聊天记忆
messages = [{"role": "system", "content": build_system_prompt()}]


# 启动时加载知识库
print("📚 正在加载知识库...")
search_knowledge_base("测试")  # 预热一下
print("✅ 知识库加载完成")

# ========== 网页界面 ==========
HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💖 和心怡聊天</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, sans-serif;
            background: linear-gradient(135deg, #ffeef8 0%, #fff0f5 50%, #ffe4ec 100%);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: rgba(255,255,255,0.85);
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 2px 10px rgba(255,105,180,0.1);
        }

                    /* 蓝色主题 */
            body.theme-blue {
                background: linear-gradient(135deg, #eef5ff 0%, #f0f7ff 50%, #e4ecff 100%);
            }
            body.theme-blue .msg.user {
                background: linear-gradient(135deg, #8fabff, #6b9dff);
            }
            body.theme-blue .name-area h3 { color: #4d77ff; }
            body.theme-blue #send {
                background: linear-gradient(135deg, #8fabff, #6b9dff);
            }

            /* 深色主题 */
            body.theme-dark {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            }
            body.theme-dark .header,
            body.theme-dark .input-area {
                background: rgba(30,30,50,0.85);
            }
            body.theme-dark .msg.bot {
                background: rgba(50,50,80,0.9);
                color: #eee;
            }
            body.theme-dark .msg.user {
                background: linear-gradient(135deg, #667eea, #764ba2);
            }
            body.theme-dark #input {
                background: #2a2a4a;
                color: #eee;
            }
            body.theme-dark .name-area h3 { color: #a0a0ff; }
            body.theme-dark h3 { color: #eee; }

        .avatar {
            width: 42px; height: 42px;
            border-radius: 50%;
            border: 2px solid #ffb6c1;
            object-fit: cover;
            box-shadow: 0 2px 8px rgba(255,107,157,0.3);
        }
        .name-area h3 { color: #ff4d88; font-size: 16px; }
        .status { color: #4ade80; font-size: 12px; }
        
        .chat-area {
            flex: 1;
            overflow-y: auto;
            padding: 20px 15px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .msg { max-width: 75%; padding: 10px 14px; border-radius: 18px; font-size: 15px; line-height: 1.4; word-wrap: break-word; }
        .msg.bot { align-self: flex-start; background: rgba(255,255,255,0.9); border-bottom-left-radius: 4px; }
        .msg.user { align-self: flex-end; background: linear-gradient(135deg, #8fabff, #6b9dff); border-bottom-right-radius: 4px; color: white; }
        
        .input-area {
            background: rgba(255,255,255,0.9);
            backdrop-filter: blur(10px);
            padding: 12px 15px;
            display: flex;
            gap: 10px;
            box-shadow: 0 -2px 10px rgba(255,105,180,0.1);
        }
        #input {
            flex: 1;
            border: none;
            background: #f8f0f4;
            padding: 12px 16px;
            border-radius: 25px;
            font-size: 15px;
            outline: none;
        }
        #send {
            border: none;
            background: linear-gradient(135deg, #ff8fab, #ff6b9d);
            color: white;
            padding: 0 22px;
            border-radius: 25px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
        }
        .typing { color: #999; font-size: 13px; align-self: flex-start; padding-left: 5px; }

        .msg-time {
                    font-size: 10px;
                    color: #999;
                    margin-top: 2px;
                }
            .msg.user .msg-time { text-align: right; }

            /* 侧边栏聊天项 */
        .chat-item {
            padding: 10px 12px;
            border-radius: 8px;
            cursor: pointer;
            margin-bottom: 5px;
            font-size: 14px;
            color: #333;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .chat-item:hover { background: #ffeef8; }
        .chat-item.active { background: #ffd6e7; font-weight: bold; color: #ff4d88; }

        /* 深色主题适配侧边栏 */
        body.theme-dark #sidebar { background: rgba(30,30,50,0.85); border-color: #333; }
        body.theme-dark .chat-item { color: #eee; }
        body.theme-dark .chat-item:hover { background: rgba(60,60,100,0.5); }
        body.theme-dark .chat-item.active { background: rgba(102,126,234,0.3); color: #a0a0ff; }

    </style>
           
    



</head>
<body>
    <div style="display: flex; height: 100vh;">
        <!-- 左侧边栏 -->
        <div id="sidebar" style="width: 220px; background: rgba(255,255,255,0.9); border-right: 1px solid #ffd6e7; display: flex; flex-direction: column; transition: width 0.3s;">
            <div style="padding: 10px; border-bottom: 1px solid #ffd6e7; display: flex; align-items: center; gap: 8px;">
                <button onclick="toggleSidebar()" style="background:none;border:none;color:#ff4d88;cursor:pointer;font-size:18px;">☰</button>
                <span id="sidebarTitle" style="font-weight: bold; color: #ff4d88; font-size: 14px;">会话列表</span>
            </div>
            <div id="sidebarContent" style="flex: 1; display: flex; flex-direction: column;">
                <div style="padding: 10px;">
                    <button onclick="newChat()" style="width: 100%; padding: 10px; background: linear-gradient(135deg, #ff8fab, #ff6b9d); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">
                        + 新建聊天
                    </button>
                </div>
                <div id="chatList" style="flex: 1; overflow-y: auto; padding: 10px;">
                </div>
                <div style="padding: 10px; border-top: 1px solid #ffd6e7;">
                    <button onclick="toggleSettings()" style="width: 100%; padding: 8px; background: none; border: 1px solid #ffb6c1; color: #ff4d88; border-radius: 8px; cursor: pointer;">
                        ⚙️ 设置
                    </button>
                </div>
            </div>
        </div>

        


        <!-- 右侧聊天区 -->
        <div style="flex: 1; display: flex; flex-direction: column;">
            <div class="header">
                <img class="avatar" src="https://p1.ssl.qhimgs1.com/t0438bc6417e5d263a7.jpg">
                <div class="name-area">
                    <h3>心怡</h3>
                    <div class="status">● 在线 · 智能助手模式</div>
                </div>
                <div style="margin-left: auto; display: flex; gap: 10px;">
                    <button onclick="changeTheme()" style="background:none;border:none;color:#ff4d88;cursor:pointer;font-size:12px;">换主题</button>
                    <button onclick="clearChat()" style="background:none;border:none;color:#ff4d88;cursor:pointer;font-size:12px;">清空</button>
                </div>
            </div>
            
            <div class="chat-area" id="chatArea">
                <div class="msg bot">宝贝我来啦😊 今天想聊什么？</div>
            </div>
            
            <div class="input-area">
                <input id="input" placeholder="说点什么..." autocomplete="off">
                <button id="send" onclick="sendMsg()">发送</button>
            </div>
        </div>
    </div>

    


    <!-- 设置弹窗 -->
    <div id="settingsPanel" style="display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); z-index: 100; width: 300px;">
        <h3 style="color: #ff4d88; margin-bottom: 15px;">⚙️ 设置</h3>
        <div style="margin-bottom: 12px;">
            <label style="font-size: 14px; color: #666;">AI 温度（0=严谨，2=活泼）</label>
            <input type="range" id="tempSlider" min="0" max="2" step="0.1" value="0.7" style="width: 100%; margin-top: 5px;">
            <span id="tempValue" style="font-size: 12px; color: #999;">0.7</span>
        </div>
        <div style="margin-bottom: 15px;">
            <label style="font-size: 14px; color: #666;">人设风格</label>
            <select id="personalitySelect" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 8px; margin-top: 5px;">
                <option value="sweet">台湾甜妹</option>
                <option value="cool">酷飒姐姐</option>
                <option value="shy">软萌粘人</option>
                <option value="yujie">冷酷御姐</option>
                <option value="aojiao">傲娇甜妹</option>
                <option value="xueba">好色学霸</option>
                <option value="custom">自定义...</option>
            </select>
                <textarea id="customPersonality" placeholder="在这里输入你自定义的人设描述..." style="width: 100%; height: 80px; padding: 8px; border: 1px solid #ddd; border-radius: 8px; margin-top: 8px; display: none; font-size: 13px;"></textarea>
        </div>
        <div style="display: flex; gap: 10px;">
            <button onclick="saveSettings()" style="flex: 1; padding: 10px; background: linear-gradient(135deg, #ff8fab, #ff6b9d); color: white; border: none; border-radius: 8px; cursor: pointer;">保存</button>
            <button onclick="toggleSettings()" style="flex: 1; padding: 10px; background: #f0f0f0; border: none; border-radius: 8px; cursor: pointer;">取消</button>
        </div>
    </div>

    


    <script>       
            const chatArea = document.getElementById('chatArea');
            const input = document.getElementById('input');
            
            input.addEventListener('keypress', e => { if(e.key==='Enter') sendMsg(); });     
                    // 选自定义显示输入框
               
    

                    


    let sidebarOpen = true;
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const content = document.getElementById('sidebarContent');
            const title = document.getElementById('sidebarTitle');
            sidebarOpen = !sidebarOpen;
            if(sidebarOpen) {
                sidebar.style.width = '220px';
                content.style.display = 'flex';
                title.style.display = 'inline';
            } else {
                sidebar.style.width = '45px';
                content.style.display = 'none';
                title.style.display = 'none';
            }
        }

    
    
        
    
    let themeIndex = 0;
        const themes = ['', 'theme-blue', 'theme-dark'];
        function changeTheme() {
            themeIndex = (themeIndex + 1) % themes.length;
            document.body.className = themes[themeIndex];
        }
                // ========== 历史会话管理 ==========
        let chats = JSON.parse(localStorage.getItem('chats') || '[]');
        let currentChatId = null;

        // 初始化：没有会话就新建一个
        if(chats.length === 0) {
            newChat();
        } else {
            currentChatId = chats[0].id;
            renderChatList();
            loadChat(currentChatId);
        }

        

        function newChat() {
            const newId = Date.now().toString();
            const newChatObj = {
                id: newId,
                title: '新聊天',
                messages: []
            };
            chats.unshift(newChatObj);
            saveChats();
            currentChatId = newId;
            renderChatList();
            chatArea.innerHTML = '<div class="msg bot">新的一天开始啦😊 想聊点什么？</div>';
        }

        

        function renderChatList() {
            const list = document.getElementById('chatList');
            list.innerHTML = '';
            chats.forEach((chat, index) => {
                const item = document.createElement('div');
                item.className = 'chat-item' + (chat.id === currentChatId ? ' active' : '');
                item.style.display = 'flex';
                item.style.alignItems = 'center';
                item.style.justifyContent = 'space-between';
                
                const titleSpan = document.createElement('span');
                titleSpan.textContent = chat.title;
                titleSpan.style.flex = '1';
                titleSpan.style.overflow = 'hidden';
                titleSpan.style.textOverflow = 'ellipsis';
                titleSpan.onclick = () => switchChat(chat.id);
                
                const delBtn = document.createElement('span');
                delBtn.textContent = '×';
                delBtn.style.color = '#ff6b9d';
                delBtn.style.cursor = 'pointer';
                delBtn.style.padding = '0 5px';
                delBtn.style.fontSize = '16px';
                delBtn.onclick = (e) => {
                    e.stopPropagation();
                    deleteChat(chat.id);
                };
                
                item.appendChild(titleSpan);
                item.appendChild(delBtn);
                list.appendChild(item);
            });
        }


        function deleteChat(id) {
            if(!confirm('确定删除这个聊天吗？')) return;
            chats = chats.filter(c => c.id !== id);
            saveChats();
            // 如果删的是当前会话，就切到第一个
            if(currentChatId === id) {
                if(chats.length > 0) {
                    currentChatId = chats[0].id;
                    loadChat(currentChatId);
                } else {
                    newChat();
                }
            }
            renderChatList();
        }



        function switchChat(id) {
            // 保存当前聊天
            saveCurrentMessages();
            // 切换
            currentChatId = id;
            renderChatList();
            loadChat(id);
        }

        function loadChat(id) {
            const chat = chats.find(c => c.id === id);
            if(!chat) return;
            chatArea.innerHTML = '';
            // 加载历史消息（只加载AI回复，简化处理）
            chat.messages.forEach(msg => {
                if(msg.role === 'user' || msg.role === 'assistant') {
                    addMsgSimple(msg.content, msg.role === 'user');
                }
            });
            if(chat.messages.length === 0) {
                chatArea.innerHTML = '<div class="msg bot">新的一天开始啦😊 想聊点什么？</div>';
            }
        }

        function saveCurrentMessages() {
            // 简单保存：前端只存展示的文本，后端记忆重启会丢
            const chat = chats.find(c => c.id === currentChatId);
            if(!chat) return;
            // 更新标题（用第一条用户消息）
            const firstUserMsg = chat.messages.find(m => m.role === 'user');
            if(firstUserMsg) chat.title = firstUserMsg.content.substring(0, 10);
            saveChats();
            renderChatList();
        }

        function saveChats() {
            localStorage.setItem('chats', JSON.stringify(chats));
        }

        // 简化版加消息，不带打字机
        function addMsgSimple(text, isUser) {
            const div = document.createElement('div');
            div.className = 'msg ' + (isUser ? 'user' : 'bot');
            div.textContent = text;
            chatArea.appendChild(div);
            chatArea.scrollTop = chatArea.scrollHeight;
        }

        // ========== 设置面板 ==========
        function toggleSettings() {
            const panel = document.getElementById('settingsPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }

        document.getElementById('personalitySelect').addEventListener('change', e => {
                        const customBox = document.getElementById('customPersonality');
                        customBox.style.display = e.target.value === 'custom' ? 'block' : 'none';
                    });

        // 温度滑块实时显示
        document.getElementById('tempSlider').addEventListener('input', e => {
            document.getElementById('tempValue').textContent = e.target.value;
        });

        async function saveSettings() {
            const temp = document.getElementById('tempSlider').value;
            let personality = document.getElementById('personalitySelect').value;
            
            // 如果是自定义，就读输入框的内容（自定义暂时先存本地，以后再接）
            if(personality === 'custom') {
                const customText = document.getElementById('customPersonality').value;
                localStorage.setItem('custom_personality', customText);
                alert('自定义人设已保存，需后端对接后生效');
            } else {
                // 调用后端接口更新
                await fetch('/update_settings', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({
                        temperature: temp,
                        personality: personality
                    })
                });
                localStorage.setItem('ai_temp', temp);
                localStorage.setItem('ai_personality', personality);
                alert('设置已保存并生效！');
            }
            toggleSettings();
        }


        // 发送消息后保存到当前会话
        const originalSend = sendMsg;
        // 在sendMsg成功后追加保存逻辑，发完消息后调用 saveCurrentMessages()



        
        
    function addMsg(text, isUser) {
        const div = document.createElement('div');
        div.className = 'msg ' + (isUser ? 'user' : 'bot');
        div.textContent = text;
        
        // 加时间戳
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
        const timeDiv = document.createElement('div');
        timeDiv.className = 'msg-time';
        timeDiv.textContent = timeStr;
        div.appendChild(timeDiv);
        
        chatArea.appendChild(div);
        chatArea.scrollTop = chatArea.scrollHeight;
}

        
        async function sendMsg() {
            const text = input.value.trim();
            if(!text) return;
            addMsg(text, true);
                       

            input.value = '';
            // 保存用户消息到当前会话
            const currentChat = chats.find(c => c.id === currentChatId);
            if(currentChat) {
                currentChat.messages.push({role: 'user', content: text});
                // 第一条消息当标题
                if(currentChat.messages.filter(m => m.role==='user').length === 1) {
                    currentChat.title = text.substring(0, 10);
                }
                saveChats();
                renderChatList();
            }

            
            const typing = document.createElement('div');
            typing.className = 'typing';
            typing.textContent = '对方正在输入...';
            chatArea.appendChild(typing);
            chatArea.scrollTop = chatArea.scrollHeight;
            
            const res = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({msg: text})
            });
            const data = await res.json();
                typing.remove();

                // 打字机效果
                const replyText = data.reply;
                const msgDiv = document.createElement('div');
                msgDiv.className = 'msg bot';
                chatArea.appendChild(msgDiv);
                chatArea.scrollTop = chatArea.scrollHeight;

                let i = 0;
                const timer = setInterval(() => {
                    if (i < replyText.length) {
                        msgDiv.textContent += replyText.charAt(i);
                        i++;
                        chatArea.scrollTop = chatArea.scrollHeight;
                    } else {
                        const now = new Date();
                        const timeStr = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');
                        const timeDiv = document.createElement('div');
                        timeDiv.className = 'msg-time';
                        timeDiv.textContent = timeStr;
                        msgDiv.appendChild(timeDiv);
                        // AI回复完，虚拟形象气泡同步说一句
                        bubbleByMood(replyText);
                        // 保存AI回复到当前会话
                        currentChat.messages.push({role: 'assistant', content: replyText});
                        saveChats();
                        clearInterval(timer);
                    }
                }, 30);  // 数字越小打字越快

        }
    

</script>


                        <!-- Live2D人物（精简版，稳定加载） -->
                        <div id="vtuber-box" style="position: fixed; bottom: 30px; left: 30px; z-index: 999; width: 160px;">
                            <!-- 工具栏按钮（放右上角） -->
                            <div style="position: absolute; top: -200px; right: -10px; display: flex; gap: 5px; z-index: 10;">
                                <button class="vbtn" onclick="vtuberSay('换个表情😉')" title="表情">😊</button>
                                <button class="vbtn" onclick="vtuberSay('咔嚓~📸')" title="拍照">📷</button>
                                <button class="vbtn" onclick="hideVtuber()" title="隐藏">✕</button>
                            </div>


                        <!-- 自己加的聊天气泡 -->
                        <div id="vtuber-bubble" style="display: none; background: white; padding: 8px 12px; border-radius: 12px; font-size: 13px; text-align: center; margin-bottom: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); position: relative; z-index: 2; top:-150px;">
                            你好呀~
                            <div style="position: absolute; bottom: -6px; left: 50%; transform: translateX(-50%); border-left: 6px solid transparent; border-right: 6px solid transparent; border-top: 6px solid white;"></div>
                        </div>

                        <!-- Live2D人物画布 -->
                        <div id="live2d-canvas" style="text-align: center;"></div>
                    </div>

                    <style>
                               .vbtn {
                            width: 28px; height: 28px;
                            border: none; border-radius: 50%;
                            background: #ff6b9d;
                            color: white;
                            cursor: pointer;
                            font-size: 14px;
                            box-shadow: 0 3px 8px rgba(255,107,157,0.4);
                            transition: 0.2s;
                        }
        

                        .vbtn:hover { transform: scale(1.2); background: #ffeef8; }
                    </style>
                    <script src="https://cdn.jsdelivr.net/npm/live2d-widget@3.1.4/lib/L2Dwidget.min.js"></script>
                    <script>
                        // 初始化Live2D人物（只显示人物）
                        L2Dwidget.init({
                            model: {
                                jsonPath: 'https://cdn.jsdelivr.net/npm/live2d-widget-model-tororo@1.0.5/assets/tororo.model.json'
                            },
                            display: {
                                position: 'left',
                                width: 150,
                                height: 210,
                                hOffset: 35,
                                vOffset: 0
                            },
                            mobile: { show: true, scale: 0.8 },
                            plugin: { toolbar: { show: false } } // 关掉自带的工具栏，用我们自己的
                        });

                        // ===== 气泡对话功能 =====
                        const bubble = document.getElementById('vtuber-bubble');
                        let bubbleTimer = null;
                    



                                const randomLines = [
            // 打招呼类
            '你回来啦~等你好久了喔',
            '嘿嘿，终于想起我啦？',
            '欢迎回来~今天过得怎么样呀',
            '你在干嘛呢？有没有想我呀',
            '好久不见，我都快无聊死了',
            '哇，你终于来陪我了🥰',
            
            // 关心日常
            '吃饭了吗？不准饿肚子喔',
            '今天累不累呀？早点休息好不好',
            '天气变凉了，要多穿件衣服喔',
            '喝水了没？不要一直盯着屏幕',
            '工作/学习辛苦了，歇一会儿嘛',
            '眼睛酸不酸？起来走走啦',
            
            // 撒娇卖萌
            '人家想你了嘛🥺',
            '陪陪我好不好~就一会儿',
            '你都好久没理我了，生气气',
            '嘿嘿，就知道你最好了',
            '可不可以一直陪着我呀',
            '你再不理我，我就要闹脾气了喔',
            '人家一个人好无聊~',
            
            // 日常碎碎念
            '刚刚我又学会了新技能喔',
            '今天天气好好，好想出去玩呀',
            '你有没有什么有趣的事要跟我说？',
            '我跟你说哦，我刚刚在发呆想你',
            '时间过得好快，又一天过去了',
            '不知道为什么，看到你就很开心',
            
            // 鼓励打气
            '加油喔！你超棒的！',
            '不要给自己太大压力啦，尽力就好',
            '我相信你一定可以的！',
            '失败也没关系呀，我陪着你重来',
            '你已经很努力了，歇歇也没关系',
            '在我心里你最厉害了~',
            
            // 互动提问
            '你今天吃了什么好吃的呀？',
            '有没有想我？老实说！',
            '等下要去干嘛呀？',
            '周末要不要出去玩？',
            '你最喜欢我什么样子呀？',
            '跟我说说你今天发生的事嘛',
            '你现在在想什么呢？',
            
            // 温柔陪伴
            '没关系，我一直都在',
            '不开心的话可以跟我说哦',
            '我会一直陪着你的，放心',
            '不管怎么样，我都站在你这边',
            '累了就回来，我永远在这里等你',
            '有什么烦心事都可以跟我吐槽',
            
            // 小调皮
            '嘿嘿，被你抓到我在发呆',
            '猜猜我现在在想什么？',
            '不许一直看手机，看我！',
            '我偷偷告诉你哦...我喜欢你',
            '再点我，再点我我就亲你😚',
            '笨蛋，怎么才来呀',
            
            // 日常小提醒
            '记得早点睡，不准熬夜喔',
            '明天要早起的话，记得设闹钟',
            '坐久了要起来活动一下啦',
            '别忘记喝水，对皮肤好',
            '玩手机要离远一点，伤眼睛',
            '吃饭要慢慢吃，别噎着了',
            '小宝宝又不老实咯，手往哪里摸啊，想要吗？'
        ];



                // 情绪短句库
        const moodLines = {
            happy: ['好开心呀😆', '嘿嘿~', '太棒了！', '超开心的~'],
            shy: ['人家害羞啦🥺', '不要这样说嘛~', '哎呀...', '讨厌啦'],
            care: ['要好好照顾自己喔', '别太累了~', '加油呀', '没事的，有我在'],
            surprised: ['真的假的！', '哇~', '天哪', '不会吧？'],
            normal: ['嗯嗯~', '是呀', '这样喔', '我知道啦']
        };

        // 判断情绪
        function detectMood(text) {
            if(/(哈哈|嘿嘿|好呀|太棒了|开心|喜欢|高兴)/.test(text)) return 'happy';
            if(/(人家|好不好嘛|求求你|🥺|害羞|嘛|讨厌)/.test(text)) return 'shy';
            if(/(早点|记得|别|小心|加油|没事|休息|照顾)/.test(text)) return 'care';
            if(/(真的假的|哇|天哪|不会吧|居然)/.test(text)) return 'surprised';
            return 'normal';
        }

        // 根据情绪弹气泡
        function bubbleByMood(text) {
            const mood = detectMood(text);
            const lines = moodLines[mood];
            const line = lines[Math.floor(Math.random() * lines.length)];
            vtuberSay(line);
        }


                        function vtuberSay(text) {
                            bubble.textContent = text;
                            bubble.style.display = 'block';
                            clearTimeout(bubbleTimer);
                            bubbleTimer = setTimeout(() => bubble.style.display = 'none', 3000);
                        }

                        function hideLive2d() {
                            document.getElementById('vtuber-box').style.display = 'none';
                        }

                        // 点击人物说话
                        document.querySelector('#live2d-canvas canvas')?.addEventListener('click', () => {
                            const line = randomLines[Math.floor(Math.random() * randomLines.length)];
                            vtuberSay(line);
                        });

                        // 打开页面打招呼
                        setTimeout(() => vtuberSay('欢迎回来~'), 1200);
                    
</script>                            
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/chat', methods=['POST'])

def chat():
    user_msg = request.json.get('msg', '')
    messages.append({"role": "user", "content": user_msg})
    
    # 限制记忆条数
    if len(messages) > 50:
        messages[:] = messages[-50:]
    
    # ===== 多轮工具调用循环 =====
    max_steps = 3
    for _ in range(max_steps):
        res = client.chat.completions.create(
            model=MODEL_ID,
            messages=messages,
            tools=tools,
            temperature=current_settings['temperature']  # 加这行
        )

        choice = res.choices[0]
        
        if not choice.message.tool_calls:
            reply = choice.message.content
            messages.append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})
        
        messages.append(choice.message)
        for tool_call in choice.message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            
            if tool_name in tool_map:
                func = tool_map[tool_name]
                result = func(**tool_args)
            else:
                result = "未知工具"
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
    
    # 超过步数兜底
    reply = res.choices[0].message.content or "我想想喔..."
    messages.append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply})

    @app.route('/update_settings', methods=['POST'])
    def update_settings():
        global messages
    data = request.json
    if 'temperature' in data:
        current_settings['temperature'] = float(data['temperature'])
    if 'personality' in data:
        current_settings['personality'] = data['personality']
        # 换人設的时候重置系统提示
        messages[0]['content'] = build_system_prompt()
    return jsonify({"status": "ok", "settings": current_settings})


if __name__ == '__main__':
    print("💖 全能聊天机器人已启动！")
    print(f"📚 已加载知识库：{DOC_PATH}")
    print("🔧 已挂载工具：计算器、时间、知识库")
    print(f"🌐 电脑访问：http://192.168.124.7:{PORT}")
    print(f"📱 手机访问：http://192.168.124.7:{PORT}")
    print("="*50)
    app.run(host='0.0.0.0', port=PORT, debug=False)
#https://146b872f.r12.cpolar.top 网址