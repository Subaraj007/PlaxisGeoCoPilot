# Standard Library 
import re
from typing import Callable, Optional, List, Dict, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Third-Party Library 
import flet as ft

# Local Module 
from frontend.database_connection import DatabaseConnection
from frontend.database_config import DatabaseConfig

class InputValidator:
    @staticmethod
    def is_valid_text(value: str) -> Tuple[bool, str]:
        if not value:
            return True, ""
        # Check for special characters
        if re.search(r'[*&^%$#@!]+', value):
            return False, "Special characters are not allowed"
        return True, ""

    
    @staticmethod
    def is_valid_number(value: str) -> Tuple[bool, str]:
        if not value:
            return True, ""
        # Allow negative numbers and decimals
        try:
            float(value)
            return True, ""
        except ValueError:
            return False, "Please enter a valid number"
    @staticmethod
    def is_valid_positive_number(value: str) -> Tuple[bool, str]:
        if not value:
            return True, ""
        try:
            num = float(value)
            if num < 0:
                return False, "Please enter a positive number"
            return True, ""
        except ValueError:
            return False, "Please enter a valid number"
    
    @staticmethod
    def is_valid_integer(value: str) -> Tuple[bool, str]:
        if not value:
            return True, ""
        try:
            int(value)
            return True, ""
        except ValueError:
            return False, "Please enter a valid integer"

    @staticmethod
    def is_valid_depth(value: str) -> Tuple[bool, str]:
        if not value:
            return True, ""
        try:
            depth = float(value)
            if depth > 0:
                return False, "Depth should be negative or zero"
            return True, ""
        except ValueError:
            return False, "Please enter a valid depth"

class FormField:
    def __init__(self, label: str, field_type: str, placeholder: str = "", on_change=None,
                 options: List[str] = None, value: str = None, required: bool = False,
                 validation_type: str = None):
        self.label = label
        self.field_type = field_type
        self.placeholder = placeholder
        self.options = options or []
        self.value = value
        self.required = required
        self.validation_type = validation_type or field_type
        self.error_text = None
        self.on_change = None
        self.is_valid = True  # Initialize is_valid attribute

    def set_on_change(self, handler):
        """Set the on_change handler after initialization"""
        self.on_change = handler
        return self
    
    def validate_input(self, value: str) -> bool:
        self.error_text = None
        self.is_valid = True
        if not self.required and (value is None or str(value).strip() == ""):
            return True
        if self.required and (value is None or value.strip() == ""):
            self.error_text = "This field is required"
            self.is_valid = False  # Update is_valid state
            return False
        
        # Skip validation for empty optional fields
        if not value:
            self.error_text = None
            self.is_valid = True  # Update is_valid state
            return True
            
        validator = self._get_validator()
        is_valid, error_message = validator(value)
        
        if not is_valid:
            self.error_text = error_message
            self.is_valid = False  # Update is_valid state
            return False
            
        self.error_text = None
        self.is_valid = True
        return True
    
    def _get_validator(self) -> Callable:
        validators = {
            "text": InputValidator.is_valid_text,
            "number": InputValidator.is_valid_number,
            "positive_number": InputValidator.is_valid_positive_number,
            "integer": InputValidator.is_valid_integer,
            "depth": InputValidator.is_valid_depth
        }
        return validators.get(self.validation_type, InputValidator.is_valid_text)

    def create_control(self, width: int = 300, set_number: Optional[int] = None,
                      on_change=None, value: str = None, disabled: bool = False) -> ft.Control:
        label = f"{self.label} (Set {set_number})" if set_number else self.label
        if self.required:
            label = f"{label} *"
            
        control_value = value if value is not None else self.value
        handler = on_change if on_change is not None else self.on_change
        
        def validate_on_change(e):
            # Validate the input
            is_valid = self.validate_input(e.control.value)
            if not is_valid:
                e.control.border_color = ft.colors.RED_500
                e.control.error_text = self.error_text
                e.control.error_style = ft.TextStyle(
                    color=ft.colors.RED_500,
                    size=12,
                    weight=ft.FontWeight.NORMAL
                )
            else:
                e.control.border_color = None
                e.control.error_text = None
            
            e.control.update()
        
            if handler:
               handler(e)
               
        common_props = {
            "label": label,
            "width": width,
            "height": 45,
            "value": control_value,
            "on_change": validate_on_change,
            "disabled": disabled,
            "border_color": ft.colors.RED_500 if not self.is_valid else None,
            "error_text": self.error_text,
            "error_style": ft.TextStyle(
                color=ft.colors.RED_500,
                size=12,
                weight=ft.FontWeight.NORMAL
            ) if self.error_text else None
        }
        
        if self.field_type == "text":
            return ft.TextField(
                hint_text=self.placeholder,
                **common_props
            )
        elif self.field_type == "checkbox":
            return ft.Checkbox(
                label=label,  # Set the label for the checkbox
                value=control_value if control_value is not None else False,  # Default to False if no value is provided
                on_change=handler,  # Set the change handler
                disabled=disabled  # Set disabled state
            )
        elif self.field_type == "number":
            return ft.TextField(
                hint_text=self.placeholder,
                keyboard_type=ft.KeyboardType.NUMBER,
                **common_props
            )
        elif self.field_type == "dropdown":
            return ft.Dropdown(
                options=[ft.dropdown.Option(option) for option in self.options],
                **common_props
            )
        elif self.field_type == "constant":
            return ft.Row(
                [
                    ft.Text(f"{label}:", size=14),
                    ft.Text(f"{control_value}", weight="bold", size=14),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                width=width,
            )
        raise ValueError(f"Unsupported field type: {self.field_type}")

class FormSection(ABC):
    @abstractmethod
    def get_fields(self) -> List[FormField]:
        pass

    @abstractmethod
    def validate(self, data: Dict) -> List[str]:
        pass

    @abstractmethod
    def save(self, cursor, data: Dict) -> None:
        pass
    



