from nicegui import ui
import requests
import json
import asyncio
from .common import render_header

API_URL = 'http://localhost:8000'

@ui.page('/run')
def run_judge_page():
    render_header()
    ui.label('실험 실행').classes('text-2xl font-bold q-mb-md')
    # 프롬프트/데이터셋 리스트를 먼저 받아온다
    r = requests.get(f'{API_URL}/prompts')
    prompts = r.json().get('prompts', [])
    r = requests.get(f'{API_URL}/datasets')
    datasets = r.json().get('datasets', [])
    dataset_options = []
    for group in datasets:
        for filename in group['files']:
            dataset_options.append((f"{group['version']}/{filename}", (group['version'], filename)))
    # 프롬프트/데이터셋 선택 영역을 한 행에 배치
    with ui.row().classes('w-full flex flex-row q-pa-md').style('border: 2px solid #ccc; border-radius: 8px;'):
        # 프롬프트 선택 (왼쪽 50%)
        with ui.column().classes('flex-1 q-pa-md'):
            ui.label('프롬프트 파일')
            prompt_radio = ui.radio(prompts).classes('grid grid-cols-3')
        # 데이터셋 선택 (오른쪽 50%)
        with ui.column().classes('flex-1 q-pa-md'):
            ui.label('데이터셋 파일')
            dataset_radio = ui.radio([x[0] for x in dataset_options]).classes('grid grid-cols-2')
    result_area = ui.textarea('실험 결과').props('readonly').props('rows=24').classes('w-full')
    result_file_label = ui.label('').classes('q-mt-md')

    # 결과 파일명 입력란 추가
    result_filename_input = ui.input('결과 파일명').classes('w-full q-mb-md')

    # 파일명 자동 생성 함수
    def make_result_filename():
        pf = prompt_radio.value
        ds = dataset_radio.value
        dv, df = None, None
        for label, (v, f) in dataset_options:
            if label == ds:
                dv, df = v, f
        if pf and dv and df:
            return f"{pf.replace('.yaml','')}_{dv}_{df.replace('.json','')}.json"
        return ''

    # 프롬프트/데이터셋 선택 시마다 파일명 자동 갱신
    def update_result_filename(e=None):
        filename = make_result_filename()
        if filename:
            result_filename_input.value = filename

    prompt_radio.on('update:model-value', update_result_filename)
    dataset_radio.on('update:model-value', update_result_filename)

    async def on_run():
        prompt_filename = prompt_radio.value
        dataset_label = dataset_radio.value
        dataset_version, dataset_filename = None, None
        for label, (v, f) in dataset_options:
            if label == dataset_label:
                dataset_version, dataset_filename = v, f
        if not prompt_filename or not dataset_version or not dataset_filename:
            result_area.value = '프롬프트와 데이터셋을 모두 선택하세요.'
            return
        result_file = result_filename_input.value.strip()
        if not result_file:
            result_area.value = '결과 파일명을 입력하세요.'
            return
        data = {
            'prompt_filename': prompt_filename,
            'dataset_version': dataset_version,
            'dataset_filename': dataset_filename,
            'result_file': result_file
        }
        result_area.value = '로딩중입니다...'
        result_file_label.text = ''
        await asyncio.sleep(0)  # UI 업데이트 강제 반영
        try:
            loop = asyncio.get_event_loop()
            def post_request():
                r = requests.post(f'{API_URL}/run_judge', json=data)
                return r.json()
            res = await loop.run_in_executor(None, post_request)
            result_area.value = json.dumps(res.get('result', {}), ensure_ascii=False, indent=2)
            result_file_label.text = f"저장 파일명: {res.get('result_file', '')}"
        except Exception as e:
            result_area.value = f'Error: {e}'

    ui.button('실행', on_click=lambda e: asyncio.create_task(on_run())) 

    # N값 입력란 추가 (일관성 측정용)
    n_input = ui.number('실행 횟수(N)', value=5, min=1, max=20).classes('w-full q-mb-md')
    
    # 기존 실행 버튼 아래에 일관성 측정 버튼 추가
    async def on_consistency():
        prompt_filename = prompt_radio.value
        dataset_label = dataset_radio.value
        dataset_version, dataset_filename = None, None
        for label, (v, f) in dataset_options:
            if label == dataset_label:
                dataset_version, dataset_filename = v, f
        if not prompt_filename or not dataset_version or not dataset_filename:
            result_area.value = '프롬프트와 데이터셋을 모두 선택하세요.'
            return
        result_file = result_filename_input.value.strip()
        if not result_file:
            result_area.value = '결과 파일명을 입력하세요.'
            return
        n = n_input.value or 5
        data = {
            'prompt_filename': prompt_filename,
            'dataset_version': dataset_version,
            'dataset_filename': dataset_filename,
            'result_file': result_file,
            'n': n
        }
        result_area.value = '일관성 측정 중입니다...'
        result_file_label.text = ''
        await asyncio.sleep(0)
        try:
            loop = asyncio.get_event_loop()
            def post_request():
                r = requests.post(f'{API_URL}/run_consistency', json=data)
                return r.json()
            res = await loop.run_in_executor(None, post_request)
            result_area.value = json.dumps(res.get('metrics', {}), ensure_ascii=False, indent=2)
            result_file_label.text = f"저장 파일명: {res.get('result_file', '')}"
        except Exception as e:
            result_area.value = f'Error: {e}'

    ui.button('일관성 측정', on_click=lambda e: asyncio.create_task(on_consistency())).classes('q-mt-md') 