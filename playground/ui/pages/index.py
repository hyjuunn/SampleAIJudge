from nicegui import ui
from .common import render_header

@ui.page('/')
def main_page():
    render_header()