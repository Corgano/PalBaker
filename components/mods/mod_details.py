# components/mods/mod_details.py
import flet as ft

class ModDetails:
    def __init__(self, mod_data: dict, on_pick_icon, on_pick_audio, on_play_audio, on_clear_audio):
        self.mod_data = mod_data
        self.on_pick_icon = on_pick_icon
        self.on_pick_audio = on_pick_audio
        self.on_play_audio = on_play_audio
        self.on_clear_audio = on_clear_audio
        
        # --- ICON SLOT COMPONENT ---
        has_icon = mod_data.get("has_icon", False)
        icon_path = mod_data.get("icon_path", "")
        
        if has_icon and icon_path:
            content = ft.Image(src=icon_path, width=64, height=64, fit=ft.BoxFit.CONTAIN)
        else:
            content = ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE, size=32, color=ft.Colors.WHITE54)

        self.icon_slot = ft.Container(
            content=content,
            width=64,
            height=64,
            border=ft.Border.all(1, ft.Colors.WHITE24),
            border_radius=8,
            ink=True,
            on_click=self.handle_icon_click,
            tooltip="Click to set custom Pal Icon"
        )

        icon_section = ft.Column([
            ft.Text("Pal Icon", size=11, weight=ft.FontWeight.BOLD),
            self.icon_slot
        ], spacing=5)

        # --- AUDIO CUSTOMIZATION SECTION ---
        audio_section_controls = []
        has_fmodel = mod_data.get("has_fmodel", False)
        sound_meta = mod_data.get("sound_metadata", {})

        if not has_fmodel:
            audio_section_controls.append(
                ft.Text(
                    "Audio replacement requires raw FModel files.\nPlease click 'Create .blend file' or 'Generate Sources' first.",
                    size=11,
                    color=ft.Colors.WHITE38,
                    italic=True
                )
            )
        elif not sound_meta:
            audio_section_controls.append(
                ft.Text(
                    "No mapped database found for this Pal.",
                    size=11,
                    color=ft.Colors.WHITE38,
                    italic=True
                )
            )
        else:
            audio_section_controls.append(
                ft.Text("Custom Pal Cries (.wav, .mp3, .ogg)", size=11, weight=ft.FontWeight.BOLD)
            )
            
            col1_controls = []
            col2_controls = []
            audio_overrides = mod_data.get("audio_overrides", {})
            available_cries = [c for c in ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"] if c in sound_meta]

            for i, cry_name in enumerate(available_cries):
                is_set = audio_overrides.get(cry_name) is not None
                color = ft.Colors.GREEN_400 if is_set else ft.Colors.WHITE30
                status_text = "Custom Override" if is_set else "Original Game Sound"

                cry_row = ft.Container(
                    content=ft.Row([
                        # Preview Audio Button (binds directly, passes cry_name via data)
                        ft.IconButton(
                            icon=ft.Icons.PLAY_ARROW_ROUNDED,
                            icon_size=16,
                            icon_color=ft.Colors.CYAN_400,
                            data=cry_name,
                            tooltip=f"Preview {cry_name}",
                            on_click=self.handle_play_click
                        ),
                        ft.Column([
                            ft.Text(cry_name, size=11, weight=ft.FontWeight.BOLD),
                            ft.Text(status_text, size=9, color=color)
                        ], spacing=1, expand=True),
                        # Upload File Button
                        ft.IconButton(
                            icon=ft.Icons.UPLOAD_FILE_ROUNDED,
                            icon_size=16,
                            data=cry_name,
                            tooltip=f"Set custom sound for {cry_name}",
                            on_click=self.handle_upload_click
                        ),
                        # Revert/Clear File Button
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                            icon_size=16,
                            icon_color=ft.Colors.RED_400,
                            data=cry_name,
                            tooltip=f"Revert {cry_name} to original",
                            on_click=self.handle_clear_click,
                            visible=is_set
                        )
                    ], spacing=2),
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=6,
                    padding=2,
                    bgcolor=ft.Colors.WHITE10 if is_set else None
                )

                if i % 2 == 0:
                    col1_controls.append(cry_row)
                else:
                    col2_controls.append(cry_row)

            audio_section_controls.append(
                ft.Row([
                    ft.Column(col1_controls, spacing=5, expand=True),
                    ft.Column(col2_controls, spacing=5, expand=True)
                ], spacing=20, expand=True)
            )

        audio_section = ft.Column(audio_section_controls, spacing=5, expand=True)

        self.view = ft.Container(
            content=ft.Row([
                icon_section,
                ft.VerticalDivider(width=1, color=ft.Colors.WHITE10),
                audio_section
            ], spacing=20, vertical_alignment=ft.CrossAxisAlignment.START),
            padding=ft.Padding(left=40, top=10, right=10, bottom=10),
            bgcolor=ft.Colors.WHITE10,
            border_radius=8
        )

    async def handle_icon_click(self, e):
        await self.on_pick_icon(self.mod_data)

    async def handle_play_click(self, e):
        await self.on_play_audio(self.mod_data, e.control.data)

    async def handle_upload_click(self, e):
        await self.on_pick_audio(self.mod_data, e.control.data)

    async def handle_clear_click(self, e):
        await self.on_clear_audio(self.mod_data, e.control.data)