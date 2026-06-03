# components/mods/dialogs.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QWidget
from PyQt6.QtCore import Qt
from utils.theme import Theme  # <--- UPDATED

class OverwriteWarningDialog(QDialog):
    def __init__(self, files, on_confirm, on_cancel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning: Overwrite Unreal Assets?")
        self.setModal(True)
        self.setStyleSheet(Theme.get_dialog_style())  # <--- UPDATED
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        msg = QLabel(
            "You have manually modified files inside Unreal Engine since your last Push.\n"
            "Continuing will OVERWRITE and delete those changes.\n\n"
            "Modified files:"
        )
        msg.setStyleSheet(f"font-size: {Theme.FONT_SIZE_NORMAL};")  # <--- UPDATED
        layout.addWidget(msg)
        
        files_str = "\n".join([f" • {f}" for f in files])
        files_lbl = QLabel(files_str)
        files_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        files_lbl.setStyleSheet(f"color: {Theme.ERROR}; font-family: {Theme.FONT_FAMILY_MONO}; font-size: {Theme.FONT_SIZE_SMALL};")  # <--- UPDATED
        layout.addWidget(files_lbl)
        
        confirm_lbl = QLabel("Are you sure you want to proceed?")
        confirm_lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(confirm_lbl)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(lambda: (self.reject(), on_cancel()))
        
        confirm_btn = QPushButton("Overwrite & Proceed")
        confirm_btn.setStyleSheet(f"background-color: {Theme.ERROR}; font-weight: bold;")  # <--- UPDATED
        confirm_btn.clicked.connect(lambda: (self.accept(), on_confirm()))
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)


class DecompileOptionsDialog(QDialog):
    def __init__(self, on_missing_only, on_overwrite_all, on_cancel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Source Assets")
        self.setModal(True)
        self.setStyleSheet(Theme.get_dialog_style())  # <--- UPDATED
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        msg = QLabel(
            "This process will reverse-engineer your ModKit's compiled .uassets back "
            "into editable Blender and PNG source files.\n\n"
            "Choose an extraction mode:"
        )
        layout.addWidget(msg)
        
        safe_lbl = QLabel(" • Generate Missing Only (Safest — leaves existing files alone)")
        safe_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: {Theme.FONT_SIZE_SMALL};")  # <--- UPDATED
        layout.addWidget(safe_lbl)
        
        force_lbl = QLabel(" • Overwrite & Regenerate (Wipes local source folder)")
        force_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: {Theme.FONT_SIZE_SMALL};")  # <--- UPDATED
        layout.addWidget(force_lbl)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(lambda: (self.reject(), on_cancel()))
        
        missing_btn = QPushButton("Missing Only")
        missing_btn.clicked.connect(lambda: (self.accept(), on_missing_only()))
        
        all_btn = QPushButton("Overwrite All")
        all_btn.setStyleSheet(f"background-color: {Theme.ERROR}; font-weight: bold;")  # <--- UPDATED
        all_btn.clicked.connect(lambda: (self.accept(), on_overwrite_all()))
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(missing_btn)
        btn_layout.addWidget(all_btn)
        layout.addLayout(btn_layout)


class TroubleshootingAdvisorDialog(QDialog):
    def __init__(self, summary, on_dismiss, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setStyleSheet(Theme.get_dialog_style())  # <--- UPDATED
        
        status = summary.get("status", "")
        title_text = "Troubleshooting Advisor"
        title_color = Theme.CYAN_ACCENT  # <--- UPDATED
        
        if status == "success_with_warnings":
            title_text = "Execution Warnings Detected"
            title_color = Theme.WARNING  # <--- UPDATED
        elif status in ["success_with_errors", "failed"]:
            title_text = "Execution Failures Encountered"
            title_color = Theme.ERROR  # <--- UPDATED

        self.setWindowTitle(title_text)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        header = QLabel(title_text)
        header.setStyleSheet(f"font-size: {Theme.FONT_SIZE_TITLE}; font-weight: bold; color: {title_color};")  # <--- UPDATED
        layout.addWidget(header)
        
        matched_rules = summary.get("matched_rules", [])
        if not matched_rules:
            layout.addWidget(QLabel("The operation completed with unexpected compiler or execution errors."))
            desc = QLabel("Please review the red error messages inside the Build Console.")
            desc.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: {Theme.FONT_SIZE_NORMAL};")  # <--- UPDATED
            layout.addWidget(desc)
        else:
            layout.addWidget(QLabel("PalBaker Diagnostics identified the following project issues:"))
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFixedHeight(220)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            
            for rule in matched_rules:
                card = QFrame()
                card.setStyleSheet(f"background-color: {Theme.BG_SURFACE}; border: 1px solid {Theme.BORDER_COLOR}; border-radius: {Theme.RADIUS_MEDIUM}; padding: 10px;")  # <--- UPDATED
                card_layout = QVBoxLayout(card)
                
                card_title = QLabel(rule["title"])
                card_title.setStyleSheet(f"font-weight: bold; color: {Theme.WARNING}; font-size: {Theme.FONT_SIZE_LARGE};")  # <--- UPDATED
                card_layout.addWidget(card_title)
                
                card_sol = QLabel(rule["solution"])
                card_sol.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: {Theme.FONT_SIZE_SMALL};")  # <--- UPDATED
                card_sol.setWordWrap(True)
                card_layout.addWidget(card_sol)
                
                assets = rule.get("assets", [])
                if assets:
                    displayed_assets = assets[:5]
                    if len(assets) > 5:
                        displayed_assets.append(f"...and {len(assets) - 5} more files.")
                    assets_str = "Violating Files:\n" + "\n".join([f" • {a}" for a in displayed_assets])
                    
                    asset_lbl = QLabel(assets_str)
                    asset_lbl.setStyleSheet(f"color: {Theme.ERROR}; font-family: {Theme.FONT_FAMILY_MONO}; font-size: {Theme.FONT_SIZE_SMALL};")  # <--- UPDATED
                    card_layout.addWidget(asset_lbl)
                    
                scroll_layout.addWidget(card)
                
            scroll.setWidget(scroll_widget)
            layout.addWidget(scroll)
            
        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.clicked.connect(lambda: (self.accept(), on_dismiss()))
        layout.addWidget(dismiss_btn)


def create_overwrite_warning_dialog(parent, files, on_confirm, on_cancel):
    return OverwriteWarningDialog(files, on_confirm, on_cancel, parent)

def create_decompile_options_dialog(parent, on_missing_only, on_overwrite_all, on_cancel):
    return DecompileOptionsDialog(on_missing_only, on_overwrite_all, on_cancel, parent)

def create_troubleshooting_advisor_dialog(parent, summary, on_dismiss):
    return TroubleshootingAdvisorDialog(summary, on_dismiss, parent)