from nicegui import ui
from ..common import render_header
import requests
import json
import os

API_URL = 'http://localhost:8000'

@ui.page('/datasets')
def dataset_list_and_detail_page():
    render_header()
    ui.label('데이터셋 목록').classes('text-2xl font-bold q-mb-md')
    r = requests.get(f'{API_URL}/datasets')
    datasets = r.json().get('datasets', [])
    def show_detail(version, filename):
        r = requests.get(f'{API_URL}/datasets/{version}/{filename}')
        content = r.json()
        selected_content.value = json.dumps(content, ensure_ascii=False, indent=2)
    def show_add_dataset():
        # 버전 목록
        version_list = [d['version'] for d in datasets]
        with ui.dialog() as dialog, ui.card().classes('w-[600px] max-w-full'):
            ui.label('데이터셋 추가').classes('text-xl font-bold')
            version = ui.select(version_list, label='버전 선택').classes('w-full')
            filename = ui.input('제목(.json 포함)').classes('w-full')
            content = ui.textarea('내용').props('rows=20').classes('w-full')
            error_label = ui.label('').classes('text-red-500')
            def submit():
                if not filename.value.endswith('.json'):
                    error_label.text = '제목은 .json으로 끝나야 합니다.'
                    return
                if not version.value:
                    error_label.text = '버전을 선택하세요.'
                    return
                r = requests.post(f'{API_URL}/datasets/{version.value}', data={'filename': filename.value, 'content': content.value})
                if r.status_code == 200:
                    dialog.close()
                    ui.notify('데이터셋이 추가되었습니다.')
                    # 목록 갱신
                    r2 = requests.get(f'{API_URL}/datasets')
                    datasets.clear()
                    datasets.extend(r2.json().get('datasets', []))
                else:
                    error_label.text = r.json().get('detail', '오류 발생')
            with ui.row():
                ui.button('확인', on_click=submit, color='primary')
                ui.button('취소', on_click=lambda: dialog.close())
    ui.button('데이터셋 추가', on_click=show_add_dataset, color='primary').classes('q-mb-md')
    with ui.column().classes('w-full flex flex-row items-start justify-start'):
        for d in datasets:
            version = d['version']
            for filename in d['files']:
                ui.button(f'{version}/{filename}', on_click=lambda v=version, fn=filename: show_detail(v, fn)).classes('q-mb-sm')
    selected_content = ui.textarea('내용', value='').props('readonly').props('rows=40').style('min-height: 300px;').classes('w-full')