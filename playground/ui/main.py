from nicegui import ui

from pages import index
from pages.prompts import index as prompts_index
from pages.datasets import index as datasets_index
from pages.results import index as results_index
from pages.consistency import index as consistency_index
from pages.consistency.index import consistency_results_page
from pages import run

ui.run(title='AI 프롬프트 실험 기록') 