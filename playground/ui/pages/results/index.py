from nicegui import ui
from ..common import render_header
import requests
import json

API_URL = 'http://localhost:8000'

@ui.page('/results')
def result_list_and_detail_page():
    render_header()
    ui.label('실험 결과 목록').classes('text-2xl font-bold q-mb-md')
    r = requests.get(f'{API_URL}/results')
    results = r.json().get('results', [])
    def show_detail(filename):
        r = requests.get(f'{API_URL}/results/{filename}')
        content = r.json()
        selected_content.value = json.dumps(content, ensure_ascii=False, indent=2)

    with ui.column().classes('w-full flex flex-row items-start justify-start'):
        for filename in results:
            ui.button(filename, on_click=lambda fn=filename: show_detail(fn)).classes('q-mb-sm')
    selected_content = ui.textarea('내용', value='').props('readonly').props('rows=40').style('min-height: 300px;').classes('w-full')