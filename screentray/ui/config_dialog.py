"""Configuration dialog for user settings."""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox,
    QDialogButtonBox, QLabel, QWidget
)
from PyQt5.QtCore import Qt
import os
import json
from typing import Dict, Any, Optional

USER_CONFIG_PATH = os.path.expanduser("~/.config/screentray/settings.json")


def load_user_config() -> Dict[str, Any]:
    """Load user configuration from file."""
    if os.path.exists(USER_CONFIG_PATH):
        try:
            with open(USER_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_user_config(config: Dict[str, Any]) -> None:
    """Save user configuration to file."""
    os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)
    with open(USER_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


class ConfigDialog(QDialog):
    """Dialog for configuring ScreenTray settings."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ScreenTray Settings")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownArgumentType]
        self.setMinimumWidth(350)

        # Load current settings
        from ..config import settings
        self.user_config = load_user_config()

        # Main layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Form layout for settings
        form = QFormLayout()

        # Alert threshold
        self.alert_spin = QSpinBox()
        self.alert_spin.setMinimum(5)
        self.alert_spin.setMaximum(240)
        self.alert_spin.setSuffix(" minutes")
        self.alert_spin.setValue(self.user_config.get('alert_session_minutes', settings.alert_session_minutes))
        form.addRow("Alert after:", self.alert_spin)

        alert_help = QLabel("Show notification after continuous active time")
        alert_help.setStyleSheet("color: gray; font-size: 10px;")
        form.addRow("", alert_help)

        # Snooze duration
        self.snooze_spin = QSpinBox()
        self.snooze_spin.setMinimum(1)
        self.snooze_spin.setMaximum(60)
        self.snooze_spin.setSuffix(" minutes")
        self.snooze_spin.setValue(self.user_config.get('snooze_minutes', settings.snooze_minutes))
        form.addRow("Snooze for:", self.snooze_spin)

        snooze_help = QLabel("Duration to postpone next alert")
        snooze_help.setStyleSheet("color: gray; font-size: 10px;")
        form.addRow("", snooze_help)

        layout.addLayout(form)
        layout.addSpacing(20)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel  # pyright: ignore[reportArgumentType, reportCallIssue]
        )
        buttons.accepted.connect(self.save_and_close)  # pyright: ignore[reportUnknownMemberType]
        buttons.rejected.connect(self.reject)  # pyright: ignore[reportUnknownMemberType]
        layout.addWidget(buttons)

    def save_and_close(self) -> None:
        """Save settings and close dialog."""
        config = {
            'alert_session_minutes': self.alert_spin.value(),
            'snooze_minutes': self.snooze_spin.value()
        }
        save_user_config(config)
        self.accept()
