from nicegui import ui
from ..common import render_header
import requests
import json

API_URL = 'http://localhost:8000'

@ui.page('/results/{filename}')
def result_detail_page(filename: str):
    render_header()
    r = requests.get(f'{API_URL}/results/{filename}')
    content = r.json()
    ui.label(f'실험 결과: {filename}').classes('text-xl font-bold q-mb-md')
    ui.textarea('내용', value=json.dumps(content, ensure_ascii=False, indent=2)).props('readonly').props('rows=40').style('min-height: 1600px;').classes('w-full')
    ui.button('목록으로', on_click=lambda: ui.navigate.to('/results')) 