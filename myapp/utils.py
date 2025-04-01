import json


# 修改：增强文件解析的健壮性
def parse_uploaded_file(file):
    try:
        # 确保文件指针回到开头
        file.seek(0)

        if file.name.endswith('.json'):
            content = file.read().decode('utf-8')
            print("原始JSON内容:", content)  # 调试输出
            data = json.loads(content)
            return [{
                'text': item.get('text', ''),
                'label1': item.get('标注信息1', item.get('label1', '')),
                'label2': item.get('标注信息2', item.get('label2', '')),
                'label3': item.get('标注信息3', item.get('label3', '')),
                'llm_answer': ''
            } for item in data]

        elif file.name.endswith('.txt'):
            # 添加更健壮的TXT解析
            return [{
                'text': line.strip(),
                'label1': '',
                'label2': '',
                'label3': '',
                'llm_answer': ''
            } for line in file.read().decode('utf-8').splitlines() if line.strip()]

    except UnicodeDecodeError:
        raise ValueError("文件编码错误，请使用UTF-8编码")
    except json.JSONDecodeError:
        raise ValueError("无效的JSON格式")