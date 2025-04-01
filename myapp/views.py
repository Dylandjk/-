import requests
from django.db import transaction
from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .models import DataRecord
from .utils import parse_uploaded_file
import json
# 修改1：添加CSRF豁免装饰器
from django.views.decorators.csrf import csrf_exempt

from django.core.serializers.json import DjangoJSONEncoder

def index(request):
    records = DataRecord.objects.all().order_by('-created_at')
    return render(request, 'myapp/index.html', {'records': records})


# 修改1：增强保存功能
@csrf_exempt
def save_data(request):
    if request.method == 'POST':
        try:
            # 调试原始数据
            raw_data = request.body.decode('utf-8')
            print("原始请求数据:", raw_data)  # 重要调试点

            parsed_data = json.loads(raw_data)
            print(f"解析到{len(parsed_data)}条数据")  # 调试日志

            # 使用事务保证原子性
            with transaction.atomic():
                # 清空旧数据（根据需求选择更新或追加）
                DataRecord.objects.all().delete()

                # 批量创建对象
                objs = [
                    DataRecord(
                        text=item.get('text', ''),
                        label1=item.get('label1', ''),
                        label2=item.get('label2', ''),
                        label3=item.get('label3', ''),
                        llm_answer=item.get('llm_answer', '')
                    ) for item in parsed_data
                ]
                DataRecord.objects.bulk_create(objs)

                # 验证保存结果
                saved_count = DataRecord.objects.count()
                print(f"当前数据库记录数: {saved_count}")

            return JsonResponse({
                'status': 'success',
                'count': len(objs),
                'saved_count': saved_count
            })

        except Exception as e:
            error_msg = f"保存失败: {str(e)}"
            print(error_msg)
            return JsonResponse({'status': 'error', 'message': error_msg})
    return JsonResponse({'status': 'error', 'message': '无效请求方法'})


@csrf_exempt  # 添加这个装饰器
def upload_file(request):
    if request.method == 'POST':
        print("收到上传请求，文件列表:", request.FILES)  # 调试日志
        if 'file' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': '未收到文件'})

        uploaded_file = request.FILES['file']
        print("收到文件:", uploaded_file.name)  # 调试日志
        try:
            parsed_data = parse_uploaded_file(uploaded_file)
            print("解析结果:", parsed_data)  # 调试日志

            # 使用事务保证数据一致性
            with transaction.atomic():
                DataRecord.objects.bulk_create([
                    DataRecord(**item) for item in parsed_data
                ])

            return JsonResponse({'status': 'success', 'count': len(parsed_data)})
        except Exception as e:
            print("文件处理错误:", str(e))  # 错误日志
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效请求方法'})@csrf_exempt  # 添加这个装饰器


def download_data(request):
    """增强版下载视图"""
    # 参数处理
    raw_format = request.GET.get('format', '').lower().strip()
    format_mapping = {
        'json': 'json',
        'txt': 'txt',
        'text': 'txt',
        'csv': 'txt',
        'tsv': 'txt'
    }

    # 获取实际格式
    actual_format = format_mapping.get(raw_format)

    # 格式有效性检查
    if not actual_format:
        error_msg = (
            "支持的格式参数：\n"
            "- JSON格式：?format=json\n"
            "- 文本格式：?format=txt/text/csv/tsv\n\n"
            f"当前收到参数: {raw_format}"
        )
        return HttpResponse(error_msg, status=400, content_type='text/plain')

    # 数据查询
    records = DataRecord.objects.all().values(
        'text', 'label1', 'label2', 'label3', 'llm_answer'
    )

    try:
        # TXT/CSV/TSV处理
        if actual_format == 'txt':
            # 根据参数生成不同分隔符
            delimiter = '\t' if raw_format in ['tsv', 'txt'] else ','
            extension = 'tsv' if raw_format == 'tsv' else 'txt'

            content = f"text{delimiter}label1{delimiter}label2{delimiter}label3{delimiter}llm_answer\n"
            for record in records:
                row = delimiter.join([
                    str(record['text']).replace('\n', ' '),
                    str(record['label1']),
                    str(record['label2']),
                    str(record['label3']),
                    str(record['llm_answer'])
                ])
                content += row + "\n"

            response = HttpResponse(
                content,
                content_type='text/plain; charset=utf-8'
            )
            filename = f'data_export.{extension}'

        # JSON处理
        else:
            data = list(records)
            response = HttpResponse(
                json.dumps(data, ensure_ascii=False, indent=2),
                content_type='application/json; charset=utf-8'
            )
            filename = 'data_export.json'

        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # 添加缓存控制头
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        return response

    except Exception as e:
        return HttpResponse(
            f"文件生成错误: {str(e)}",
            status=500,
            content_type='text/plain'
        )

def generate_answer(request):
    """支持自定义prompt"""
    if request.method == 'POST':
        text = request.POST.get('text', '')
        custom_prompt = request.POST.get('prompt', '')

        try:
            # 调用 API
            response = requests.post(
                'https://api.suanli.cn/v1/chat/completions',
                headers={
                    'Authorization': 'sk-W0rpStc95T7JVYVwDYc29IyirjtpPPby6SozFMQr17m8KWeo',
                    'Content-Type': 'application/json'
                },
                json={
                    "model": "free:QwQ-32B",
                    "messages": [
                        {"role": "user", "content": custom_prompt}
                    ]
                }
            )

            # 解析响应
            answer = response.json()['choices'][0]['message']['content']
            return JsonResponse({'status': 'success', 'answer': answer})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})