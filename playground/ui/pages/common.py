from nicegui import ui

def render_header():
    with ui.header().classes('bg-primary text-white'):
        ui.label('AI 프롬프트 실험 기록 사이트').classes('text-xl font-bold').on('click', lambda: ui.navigate.to('/')).style('cursor: pointer;')
        with ui.row().classes('gap-4'):
            ui.button('프롬프트 목록', on_click=lambda: ui.navigate.to('/prompts'))
            ui.button('데이터셋 목록', on_click=lambda: ui.navigate.to('/datasets'))
            ui.button('실험 실행', on_click=lambda : ui.navigate.to('/run'))
            ui.button('일관성 결과', on_click=lambda : ui.navigate.to('/consistency_results'))
            ui.button('실험 결과', on_click=lambda: ui.navigate.to('/results')) 