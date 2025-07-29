from nicegui import ui
import os
import json
from ..common import render_header

RESULTS_DIR = os.path.join('playground', 'results', 'consistency')

@ui.page('/consistency_results')
def consistency_results_page():
    render_header()
    ui.label('일관성 측정 결과 목록').classes('text-2xl font-bold q-mb-md')

    files = []
    if os.path.exists(RESULTS_DIR):
        files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.json')]
        files.sort(reverse=True)

    # selected_file, result_data를 일반 변수로 선언
    selected_file = ''
    result_data = None

    def load_file(filename):
        nonlocal selected_file, result_data
        if not filename:
            # 재측정: 현재 선택된 파일로 metrics만 다시 계산
            if not selected_file:
                ui.notify('먼저 결과 파일을 선택하세요.', type='warning')
                return
            import requests
            url = 'http://localhost:8000/recalc_consistency'
            try:
                resp = requests.post(url, json={'result_file': selected_file})
                if resp.status_code == 200:
                    new_metrics = resp.json().get('metrics', {})
                    if result_data:
                        result_data['metrics'] = new_metrics
                    show_details.refresh()
                    ui.notify('지표가 재계산되었습니다.', type='positive')
                else:
                    ui.notify(f'지표 재계산 실패: {resp.text}', type='negative')
            except Exception as e:
                ui.notify(f'API 호출 오류: {e}', type='negative')
            return
        path = os.path.join(RESULTS_DIR, filename)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result_data = data
        selected_file = filename
        show_details.refresh()  # 상태 변경 시 상세 결과 갱신

    

    with ui.column().classes('w-full'):
        # 지표별 일관성 기준 안내
        with ui.expansion('일관성 지표 해설 및 기준', icon='info').classes('q-mb-md'):
            ui.markdown('''
**일관성 지표별 이상적 값 제안**

| 지표명                | 엄격 기준         | 일반 기준         | 가벼운 기준        | 설명 | 계산 방식 |
|----------------------|------------------|------------------|-------------------|------|-----------|
| winner_consistency   | 1.0              | ≥0.9             | ≥0.7              | 승리 진영 일치율 (1에 가까울수록 좋음) | 여러 번 실행 결과에서 가장 많이 나온 승리 진영의 비율 |
| win_rate_similarity  | 1.0              | ≥0.95            | ≥0.8              | 승률 유사성 (1에 가까울수록 좋음) | 각 실행별 승리 진영의 percentage 표준편차/평균 |
| explanation_similarity | 1.0            | ≥0.95            | ≥0.8              | 해설 문장 유사도 (1에 가까울수록 좋음) | 해설(결론) 문장들의 코사인 유사도 평균 |
| vocab_diversity      | ≤0.05            | ≤0.1             | ≤0.2              | 어휘 다양성 (0에 가까울수록 좋음) | 해설 전체에서 고유 단어 수 / 전체 단어 수 |
| length_mean          | (적당, 50~500)    | (적당, 30~700)    | (너무 짧지만 않게) | 해설 평균 길이 | 해설(결론) 문장들의 평균 길이 |
| length_std           | 0                | ≤10              | ≤30               | 해설 길이 표준편차 (0에 가까울수록 좋음) | 해설(결론) 문장들의 길이 표준편차 |

- **엄격 기준**: 거의 완벽하게 일관적일 때
- **일반 기준**: 실무에서 충분히 일관적이라고 볼 수 있는 수준
- **가벼운 기준**: 어느 정도 일관성이 있다고 볼 수 있는 최소 기준
''')
        with ui.column().classes('w-full flex-1'):
            ui.label('결과 파일 목록').classes('font-bold')
            with ui.row().classes('w-full q-mb-xs'):
                for f in files:
                    ui.button(f, on_click=lambda e, fname=f: load_file(fname))
        with ui.column().classes('w-full flex-1'):
            with ui.row().classes('w-full q-mb-xs items-center'):
                ui.label('상세 결과').classes('font-bold')
                ui.button('재측정', on_click=lambda: load_file('')).classes('q-ml-xs')
            @ui.refreshable
            def show_details():
                if not result_data:
                    ui.label('결과 파일을 선택하세요.')
                    return
                d = result_data
                with ui.row().classes('w-full'):
                    with ui.column().classes('flex-1'):
                        ui.label(f"파일명: {selected_file}").classes('q-mb-xs')
                        ui.label(f"프롬프트: {d.get('prompt_filename')}")
                        ui.label(f"데이터셋: {d.get('dataset_version')}/{d.get('dataset_filename')}")
                        ui.label(f"실행 횟수: {d.get('n')}")
                        ui.label('지표 요약:').classes('q-mt-md font-bold')
                        m = d.get('metrics', {})
                        for k, v in m.items():
                            ui.label(f"{k}: {v}")
                    with ui.column().classes('flex-1'):
                        ui.label('원본 결과:').classes('q-mt-md font-bold')
                        ui.textarea('원본', value=json.dumps(d.get('results', []), ensure_ascii=False, indent=2)).props('rows=40').props('readonly').classes('w-full')
            show_details() 