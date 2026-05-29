# components/common/path_picker.py
import flet as ft

class PathPicker:
    def __init__(self, label: str, value: str, icon: str, on_browse_click):
        self.text_field = ft.TextField(
            label=label, 
            value=value, 
            expand=True,
            on_change=self._on_text_change
        )
        self.button = ft.IconButton(icon, on_click=on_browse_click)
        
        # Expose the layout tree
        self.view = ft.Row([self.text_field, self.button])

    def _on_text_change(self, e):
        # Update the internal value when typed manually
        self.text_field.value = e.control.value

    def get_value(self) -> str:
        return str(self.text_field.value)

    def set_value(self, value: str):
        self.text_field.value = value
        try:
            self.text_field.update()
        except Exception:
            pass