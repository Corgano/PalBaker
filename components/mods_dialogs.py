# components/mods_dialogs.py
import flet as ft

def create_overwrite_warning_dialog(files: list, on_confirm, on_cancel) -> ft.AlertDialog:
    """Creates the warning modal displayed before overriding local files."""
    files_str = "\n".join([f" • {f}" for f in files])
    return ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Warning: Overwrite Unreal Assets?"),
        content=ft.Column([
            ft.Text("You have manually modified files inside Unreal Engine since your last Push.\nContinuing will OVERWRITE and delete those changes.\n\nModified files:"),
            ft.Text(files_str, color=ft.Colors.RED_400, size=12, selectable=True),
            ft.Text("Are you sure you want to proceed?", weight=ft.FontWeight.BOLD)
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=on_cancel),
            ft.TextButton("Overwrite & Proceed", on_click=on_confirm, style=ft.ButtonStyle(color=ft.Colors.RED)),
        ]
    )

def create_decompile_options_dialog(on_missing_only, on_overwrite_all, on_cancel) -> ft.AlertDialog:
    """Creates the decompiler configuration modal offering partial vs full asset reconstruction."""
    return ft.AlertDialog(
        open=True,
        modal=True,
        title=ft.Text("Generate Source Assets"),
        content=ft.Column([
            ft.Text("This process will reverse-engineer your ModKit's compiled .uassets back into editable Blender and PNG source files.\n\nChoose an extraction mode:"),
            ft.Text(" • Generate Missing Only (Safest — leaves existing files alone)", size=12, color=ft.Colors.WHITE70),
            ft.Text(" • Overwrite & Regenerate (Wipes local source folder)", size=12, color=ft.Colors.WHITE70),
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=on_cancel),
            ft.TextButton("Missing Only", on_click=on_missing_only),
            ft.TextButton("Overwrite All", on_click=on_overwrite_all, style=ft.ButtonStyle(color=ft.Colors.RED)),
        ]
    )

def create_troubleshooting_advisor_dialog(summary: dict, on_dismiss) -> ft.AlertDialog:
    """Creates the compiler/decompiler diagnostic advisory overlay on failure."""
    matched_rules = summary.get("matched_rules", [])
    if not matched_rules:
        content = ft.Column([
            ft.Text("The operation completed with unexpected compiler or execution errors.", weight=ft.FontWeight.BOLD),
            ft.Text("Please review the red error messages inside the Build Console at the bottom of the screen.", size=13, color=ft.Colors.WHITE70)
        ], tight=True)
    else:
        cards = []
        for rule in matched_rules:
            cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(rule["title"], weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_400, size=14),
                        ft.Text(rule["solution"], size=12, color=ft.Colors.WHITE70),
                    ], spacing=5),
                    padding=12,
                    border=ft.Border.all(1, ft.Colors.WHITE24),
                    border_radius=6,
                    bgcolor=ft.Colors.WHITE10
                )
            )
        content = ft.Column([
            ft.Text("PalBaker Diagnostics identified the following project issues:", weight=ft.FontWeight.BOLD),
            ft.Column(cards, spacing=10, scroll=ft.ScrollMode.AUTO, height=200)
        ], tight=True, spacing=15)

    return ft.AlertDialog(
        title=ft.Text("Troubleshooting Advisor", color=ft.Colors.CYAN_400),
        content=content,
        actions=[
            ft.TextButton("Dismiss", on_click=on_dismiss)
        ]
    )