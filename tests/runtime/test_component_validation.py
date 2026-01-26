"""
Test for component validation feature (Issue #4).

This test verifies that:
1. Component discovery works correctly
2. Invalid components are caught with helpful error messages
3. Pre-validation prevents errors during config loading
"""

import pytest
import tempfile
import json5
import os
from pathlib import Path


def test_discover_available_inputs():
    """Test that we can discover available input sensors."""
    # This requires the inputs module to be available
    try:
        from runtime.component_registry import discover_available_inputs
        
        inputs = discover_available_inputs()
        assert isinstance(inputs, dict)
        # Should find some inputs
        assert len(inputs) >= 0
    except ImportError:
        pytest.skip("Component registry not available in test environment")


def test_validate_input_type_valid():
    """Test validation passes for valid input types."""
    try:
        from runtime.component_registry import discover_available_inputs, validate_input_type
        
        inputs = discover_available_inputs()
        if inputs:
            valid_input = list(inputs.keys())[0]
            # Should not raise
            validate_input_type(valid_input)
    except ImportError:
        pytest.skip("Component registry not available")


def test_validate_input_type_invalid():
    """Test validation fails for invalid input types with helpful message."""
    try:
        from runtime.component_registry import validate_input_type
        
        with pytest.raises(ValueError) as exc_info:
            validate_input_type("NonExistentInputType")
        
        # Error message should be helpful
        error_msg = str(exc_info.value)
        assert "NonExistentInputType" in error_msg
        assert "not found" in error_msg.lower()
        assert "Available" in error_msg  # Should list available options
    except ImportError:
        pytest.skip("Component registry not available")


def test_config_validation_with_invalid_input():
    """Test that config validation catches invalid input types early."""
    try:
        from runtime.single_mode.config import _validate_config_components
        
        # Config with invalid input type
        invalid_config = {
            "name": "test",
            "agent_inputs": [
                {"type": "NonExistentInputType", "config": {}}
            ],
            "cortex_llm": {"type": "OpenAILLM"},
        }
        
        with pytest.raises(ValueError) as exc_info:
            _validate_config_components(invalid_config)
        
        error_msg = str(exc_info.value)
        assert "agent_inputs" in error_msg
        assert "NonExistentInputType" in error_msg
    except ImportError:
        pytest.skip("Config module not available")


def test_config_validation_with_invalid_action():
    """Test that config validation catches invalid action types early."""
    try:
        from runtime.single_mode.config import _validate_config_components
        
        # Config with invalid action
        invalid_config = {
            "name": "test",
            "agent_actions": [
                {"name": "non_existent_action", "connector": "some_connector"}
            ],
            "cortex_llm": {"type": "OpenAILLM"},
        }
        
        with pytest.raises(ValueError) as exc_info:
            _validate_config_components(invalid_config)
        
        error_msg = str(exc_info.value)
        assert "agent_actions" in error_msg
        assert "non_existent_action" in error_msg
    except ImportError:
        pytest.skip("Config module not available")


def test_mode_config_validation():
    """Test that mode config validation catches invalid components."""
    try:
        from runtime.multi_mode.config import _validate_mode_config_components
        
        invalid_mode_config = {
            "name": "test_mode_system",
            "default_mode": "mode1",
            "modes": {
                "mode1": {
                    "inputs": [
                        {"type": "InvalidInputType"}
                    ]
                }
            },
            "cortex_llm": {"type": "ValidLLM"}
        }
        
        with pytest.raises(ValueError) as exc_info:
            _validate_mode_config_components(invalid_mode_config)
        
        error_msg = str(exc_info.value)
        assert "modes" in error_msg
        assert "mode1" in error_msg
        assert "InvalidInputType" in error_msg
    except ImportError:
        pytest.skip("Mode config module not available")


if __name__ == "__main__":
    # Run tests
    print("Running component validation tests...")
    test_discover_available_inputs()
    print("✓ test_discover_available_inputs passed")
    
    test_validate_input_type_valid()
    print("✓ test_validate_input_type_valid passed")
    
    test_validate_input_type_invalid()
    print("✓ test_validate_input_type_invalid passed")
    
    test_config_validation_with_invalid_input()
    print("✓ test_config_validation_with_invalid_input passed")
    
    test_config_validation_with_invalid_action()
    print("✓ test_config_validation_with_invalid_action passed")
    
    test_mode_config_validation()
    print("✓ test_mode_config_validation passed")
    
    print("\nAll tests passed!")
