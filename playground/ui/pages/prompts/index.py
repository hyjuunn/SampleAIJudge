from nicegui import ui
from ..common import render_header
import requests
import json

API_URL = 'http://localhost:8000'

@ui.page('/prompts')
def prompt_list_and_detail_page():
    render_header()

    with ui.dialog() as dialog, ui.card().classes('w-[600px] max-w-full'):
        ui.label('프롬프트 추가').classes('text-xl font-bold')
        new_filename = ui.input('제목(.yaml 또는 .json 포함)').classes('w-full')
        content = ui.textarea('내용').props('rows=20').classes('w-full')
        error_label = ui.label('').classes('text-red-500')
        def submit():
            if not (new_filename.value.endswith('.yaml') or new_filename.value.endswith('.json')):
                error_label.text = '제목은 .yaml 또는 .json으로 끝나야 합니다.'
                return
            r = requests.post(f'{API_URL}/prompts', data={'filename': new_filename.value, 'content': content.value})
            if r.status_code == 200:
                dialog.close()
                ui.notify('프롬프트가 추가되었습니다.')
                render_prompt_list()  # 리스트 갱신
            else:
                error_label.text = r.json().get('detail', '오류 발생')
        with ui.row():
            ui.button('확인', on_click=submit, color='primary')
            ui.button('취소', on_click=lambda: dialog.close())
            
    ui.label('프롬프트 목록').classes('text-2xl font-bold q-mb-md')
    ui.button('프롬프트 추가', on_click=dialog.open, color='primary').classes('q-mb-md')
    prompts = []
    prompt_buttons_column = ui.column().classes('w-full flex flex-row items-start justify-start')
    selected_content = ui.textarea('내용', value='').props('readonly').props('rows=40').style('min-height: 300px;').classes('w-full')

    def show_detail(filename):
        r = requests.get(f'{API_URL}/prompts/{filename}')
        content = r.json()
        selected_content.value = content['content']

    def render_prompt_list():
        prompt_buttons_column.clear()
        r = requests.get(f'{API_URL}/prompts')
        prompts.clear()
        prompts.extend(r.json().get('prompts', []))
        with prompt_buttons_column:
            for filename in prompts:
                ui.button(filename, on_click=lambda fn=filename: show_detail(fn)).classes('q-mb-sm')



    render_prompt_list()

