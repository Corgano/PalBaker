# utils/theme.py

class Theme:
    # 1. Accent & UI Colors
    BG_MAIN = "#121212"
    BG_SURFACE = "#1e1e1e"
    BG_CONSOLE = "#000000"
    
    BORDER_COLOR = "#2d2d2d"
    BORDER_HOVER = "#3d3d3d"
    
    PRIMARY = "#2979ff"
    PRIMARY_HOVER = "#1565c0"
    PRIMARY_PRESSED = "#0d47a1"
    
    SUCCESS = "#66bb6a"
    WARNING = "#ffb74d"
    ERROR = "#ef5350"
    CYAN_ACCENT = "#26c6da"
    
    TEXT_MAIN = "#ffffff"
    TEXT_MUTED = "#b3b3b3"
    TEXT_DARK = "#000000"
    
    # 2. Typography
    FONT_FAMILY_MAIN = "'Segoe UI', Arial, sans-serif"
    FONT_FAMILY_MONO = "'Consolas', 'Courier New', monospace"
    
    FONT_SIZE_TINY = "9px"
    FONT_SIZE_SMALL = "11px"
    FONT_SIZE_NORMAL = "13px"
    FONT_SIZE_LARGE = "14px"
    FONT_SIZE_TITLE = "16px"
    FONT_SIZE_HEADER = "20px"
    
    # 3. Geometry & Metrics
    RADIUS_SMALL = "3px"
    RADIUS_NORMAL = "4px"
    RADIUS_MEDIUM = "6px"
    RADIUS_LARGE = "8px"
    RADIUS_CHIP = "12px"
    
    DIVIDER_HEIGHT = "2px"
    DIVIDER_WIDTH = "60px"
    SPLITTER_HANDLE_HEIGHT = "4px"
    
    @classmethod
    def get_global_stylesheet(cls):
        """Generates the primary application QSS stylesheet."""
        return f"""
            QMainWindow, QWidget {{
                background-color: {cls.BG_MAIN};
                color: {cls.TEXT_MAIN};
                font-family: {cls.FONT_FAMILY_MAIN};
                font-size: {cls.FONT_SIZE_NORMAL};
            }}
            QTabWidget::pane {{
                border: 1px solid {cls.BORDER_COLOR};
                background: {cls.BG_MAIN};
            }}
            QTabBar::tab {{
                background: {cls.BG_SURFACE};
                border: 1px solid {cls.BORDER_COLOR};
                color: {cls.TEXT_MUTED};
                padding: 10px 22px;
                margin-right: 2px;
                border-top-left-radius: {cls.RADIUS_NORMAL};
                border-top-right-radius: {cls.RADIUS_NORMAL};
            }}
            QTabBar::tab:selected {{
                background: #1a1a1a;
                color: {cls.PRIMARY};
                border-bottom: 2px solid {cls.PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background: #252525;
            }}
            QLineEdit {{
                background-color: {cls.BG_SURFACE};
                border: 1px solid {cls.BORDER_COLOR};
                border-radius: {cls.RADIUS_NORMAL};
                padding: 6px;
                color: white;
            }}
            QLineEdit:focus {{
                border: 1px solid {cls.PRIMARY};
            }}
            QPushButton {{
                background-color: {cls.BG_SURFACE};
                border: 1px solid {cls.BORDER_COLOR};
                border-radius: {cls.RADIUS_NORMAL};
                padding: 6px 12px;
                color: white;
            }}
            QPushButton:hover {{
                background-color: #2a2a2a;
            }}
            QPushButton:pressed {{
                background-color: {cls.BORDER_HOVER};
            }}
            QScrollArea {{
                border: 1px solid {cls.BORDER_COLOR};
                background-color: {cls.BG_MAIN};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {cls.BG_MAIN};
                width: 10px;
            }}
            QScrollBar::handle:vertical {{
                background: {cls.BORDER_COLOR};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {cls.BORDER_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QSplitter::handle {{
                background-color: {cls.BORDER_COLOR};
            }}
            QSplitter::handle:hover {{
                background-color: {cls.PRIMARY};
            }}
            QCheckBox {{
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                background-color: {cls.BG_SURFACE};
                border: 1px solid {cls.BORDER_COLOR};
                border-radius: {cls.RADIUS_SMALL};
            }}
            QCheckBox::indicator:checked {{
                background-color: {cls.PRIMARY};
                border: 1px solid {cls.PRIMARY};
            }}
        """

    @classmethod
    def get_chip_style(cls):
        """Specific styled override for tags and chips."""
        return f"""
            QPushButton {{
                background-color: {cls.BG_SURFACE};
                border: 1px solid {cls.BORDER_HOVER};
                border-radius: {cls.RADIUS_CHIP};
                padding: 4px 12px;
                color: {cls.TEXT_MUTED};
            }}
            QPushButton:hover {{
                background-color: #2a2a2a;
            }}
            QPushButton:checked {{
                background-color: {cls.PRIMARY};
                border-color: {cls.PRIMARY};
                color: white;
            }}
        """

    @classmethod
    def get_console_style(cls):
        """Rich-text Build Console Box formatting stylesheet."""
        return f"""
            QTextEdit {{
                background-color: {cls.BG_CONSOLE};
                color: #dcdcdc;
                font-family: {cls.FONT_FAMILY_MONO};
                font-size: 12px;
                border: 1px solid {cls.BORDER_COLOR};
                border-radius: {cls.RADIUS_LARGE};
                padding: 10px;
            }}
        """

    @classmethod
    def get_card_style(cls, border_color):
        """Mod Card primary container layout boundaries."""
        return f"""
            QFrame#ModItemCard {{
                border: 1px solid {border_color};
                border-radius: {cls.RADIUS_LARGE};
                background-color: {cls.BG_MAIN};
            }}
        """

    @classmethod
    def get_details_style(cls):
        """The expandable details drawer layout wrapper stylesheet."""
        return f"""
            QWidget {{
                background-color: {cls.BG_SURFACE};
                border-radius: {cls.RADIUS_LARGE};
            }}
            QLabel {{
                background-color: transparent;
            }}
        """

    @classmethod
    def get_dialog_style(cls):
        return f"background-color: {cls.BG_MAIN}; color: white;"

    @classmethod
    def get_menu_style(cls):
        """Right-click and overflow custom options menu styling."""
        return f"""
            QMenu {{
                background-color: {cls.BG_SURFACE};
                color: white;
                border: 1px solid {cls.BORDER_COLOR};
            }}
            QMenu::item:selected {{
                background-color: {cls.PRIMARY};
            }}
        """