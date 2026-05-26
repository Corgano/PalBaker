import flet as ft
from utils.config import save_settings

class SettingsView: # Changed: Standard Python Class to bypass Flet's __getattr__ bugs
    def __init__(self, page: ft.Page, settings: dict, on_save_callback):
        self.main_page = page
        self.settings = settings
        self.on_save_callback = on_save_callback

        # Input Fields
        self.fmodel_output_field = ft.TextField(label="FModel Output Folder", value=str(settings.get("fmodel_output", "")), expand=True)
        self.ue_root_field = ft.TextField(label="Unreal Engine Root (e.g. UE_5.1)", value=str(settings.get("ue_root", "")), expand=True)
        self.uproject_field = ft.TextField(label="Palworld ModKit .uproject Path", value=str(settings.get("uproject", "")), expand=True)
        self.blender_field = ft.TextField(label="Blender Executable Path", value=str(settings.get("blender", "")), expand=True)
        self.palworld_exe_field = ft.TextField(label="Palworld.exe Path", value=str(settings.get("palworld_exe", "")), expand=True)

        # Preferences
        self.show_mapped_switch = ft.Switch(
            label="Show Mapped Names (e.g. Chillet instead of WeaselDragon)", 
            value=bool(settings.get("show_mapped", False))
        )

        # Satisfies Pylance's list covariance requirements by declaring empty list and extending
        view_controls: list[ft.Control] = []
        view_controls.extend([
            ft.Text("Application Paths", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([self.fmodel_output_field, ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=self.pick_fmodel_folder)]),
            ft.Row([self.ue_root_field, ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=self.pick_ue_root)]),
            ft.Row([self.uproject_field, ft.IconButton(ft.Icons.FILE_OPEN, on_click=self.pick_uproject)]),
            ft.Row([self.blender_field, ft.IconButton(ft.Icons.FILE_OPEN, on_click=self.pick_blender_exe)]),
            ft.Row([self.palworld_exe_field, ft.IconButton(ft.Icons.FILE_OPEN, on_click=self.pick_palworld_exe)]),
            ft.Divider(),
            ft.Text("Preferences", size=20, weight=ft.FontWeight.BOLD),
            self.show_mapped_switch,
            ft.Divider(),
            ft.ElevatedButton("Save and Reload Mod List", icon=ft.Icons.SAVE, on_click=self.save_clicked, height=50)
        ])
        
        # We store the layout column directly inside our .view property
        self.view = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=view_controls
        )

    # ---------------------------------------------------
    # Modern Async FilePickers (Flet 0.85+ Services)
    # ---------------------------------------------------
    async def pick_fmodel_folder(self, e):
        picker = ft.FilePicker()
        self.main_page.overlay.append(picker)
        self.main_page.update()
        result = await picker.get_directory_path() # type: ignore
        if result:
            self.fmodel_output_field.value = str(result)
            self.fmodel_output_field.update()
        self.main_page.overlay.remove(picker)
        self.main_page.update()

    async def pick_ue_root(self, e):
        picker = ft.FilePicker()
        self.main_page.overlay.append(picker)
        self.main_page.update()
        result = await picker.get_directory_path() # type: ignore
        if result:
            self.ue_root_field.value = str(result)
            self.ue_root_field.update()
        self.main_page.overlay.remove(picker)
        self.main_page.update()

    async def pick_uproject(self, e):
        picker = ft.FilePicker()
        self.main_page.overlay.append(picker)
        self.main_page.update()
        result = await picker.pick_files(allow_multiple=False, allowed_extensions=["uproject"]) # type: ignore
        if result and result[0].path:
            self.uproject_field.value = str(result[0].path)
            self.uproject_field.update()
        self.main_page.overlay.remove(picker)
        self.main_page.update()

    async def pick_blender_exe(self, e):
        picker = ft.FilePicker()
        self.main_page.overlay.append(picker)
        self.main_page.update()
        result = await picker.pick_files(allow_multiple=False) # type: ignore
        if result and result[0].path:
            self.blender_field.value = str(result[0].path)
            self.blender_field.update()
        self.main_page.overlay.remove(picker)
        self.main_page.update()

    async def pick_palworld_exe(self, e):
        picker = ft.FilePicker()
        self.main_page.overlay.append(picker)
        self.main_page.update()
        result = await picker.pick_files(allow_multiple=False, allowed_extensions=["exe"]) # type: ignore
        if result and result[0].path:
            self.palworld_exe_field.value = str(result[0].path)
            self.palworld_exe_field.update()
        self.main_page.overlay.remove(picker)
        self.main_page.update()

    def on_picker_result(self, e, field: ft.TextField):
        if e.path:
            field.value = e.path
        elif e.files:
            field.value = e.files[0].path
        field.update()

    def save_clicked(self, e):
        self.settings.update({
            "fmodel_output": str(self.fmodel_output_field.value),
            "ue_root": str(self.ue_root_field.value),
            "uproject": str(self.uproject_field.value),
            "blender": str(self.blender_field.value),
            "palworld_exe": str(self.palworld_exe_field.value),
            "show_mapped": bool(self.show_mapped_switch.value)
        })
        save_settings(self.settings)
        self.main_page.overlay.append(ft.SnackBar(ft.Text("Settings saved!"), open=True))
        self.main_page.update()
        self.on_save_callback()