import flet as ft
from utils.config import load_settings
from components.settings_view import SettingsView
from components.mods_view import ModsView

def main(page: ft.Page):
    page.title = "Palworld Baker Mod Manager"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 900
    page.window.height = 800
    page.padding = 20

    # Load state
    settings = load_settings()

    # Mount decoupled UI controllers
    mods_view = ModsView(page, settings)
    settings_view = SettingsView(page, settings, on_save_callback=mods_view.refresh_mods)

    # Flet 0.85+ Tabs Architecture
    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Manager", icon=ft.Icons.WIDGETS),
            ft.Tab(label="Settings", icon=ft.Icons.SETTINGS),
        ]
    )

    tab_view = ft.TabBarView(
        expand=True,
        controls=[
            mods_view.view,       # Mount the layout columns here
            settings_view.view,   # Mount the layout columns here
        ]
    )

    tabs_controller = ft.Tabs(
        length=2,
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                tab_bar,
                tab_view
            ]
        )
    )

    page.add(tabs_controller)
    mods_view.refresh_mods()

if __name__ == "__main__":
    ft.run(main)