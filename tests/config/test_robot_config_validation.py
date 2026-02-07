"""Test robot config validation at startup."""
import pytest

from runtime.single_mode.config import _check_robot_config_requirements


def test_robot_config_validation_passes_with_valid_ip():
    """Test that validation passes when robot_ip is valid."""
    config = {
        "robot_ip": "192.168.1.100",
        "agent_inputs": [{"type": "UnitreeGo2Odom", "name": "odom"}],
    }
    # Should not raise
    _check_robot_config_requirements(config)


def test_robot_config_validation_passes_without_robot_components():
    """Test that validation passes when no robot components are present."""
    config = {
        "robot_ip": None,
        "agent_inputs": [{"type": "GoogleASRInput", "name": "asr"}],
    }
    # Should not raise - no robot components
    _check_robot_config_requirements(config)


def test_robot_config_validation_fails_missing_ip_with_unitree():
    """Test that validation fails when Unitree component present but robot_ip missing."""
    config = {
        "robot_ip": None,
        "agent_inputs": [{"type": "UnitreeGo2Odom", "name": "odom"}],
    }
    with pytest.raises(ValueError) as exc_info:
        _check_robot_config_requirements(config)
    
    error_msg = str(exc_info.value)
    assert "robot_ip" in error_msg
    assert "missing or invalid" in error_msg
    assert "UnitreeGo2Odom" in error_msg
    assert "ROBOT_IP environment variable" in error_msg


def test_robot_config_validation_fails_empty_ip_with_unitree():
    """Test that validation fails when robot_ip is empty string with robot component."""
    config = {
        "robot_ip": "",
        "agent_actions": [{"type": "UnitreeGo2Move", "name": "move"}],
    }
    with pytest.raises(ValueError) as exc_info:
        _check_robot_config_requirements(config)
    
    error_msg = str(exc_info.value)
    assert "missing or invalid" in error_msg
    assert "UnitreeGo2Move" in error_msg


def test_robot_config_validation_fails_default_ip_with_ubtech():
    """Test that validation fails when robot_ip is default placeholder with UBTech."""
    config = {
        "robot_ip": "192.168.0.241",
        "agent_inputs": [{"type": "UbTechVideo", "name": "video"}],
    }
    with pytest.raises(ValueError) as exc_info:
        _check_robot_config_requirements(config)
    
    error_msg = str(exc_info.value)
    assert "missing or invalid" in error_msg


def test_robot_config_validation_identifies_multiple_robot_components():
    """Test that validation identifies all robot-dependent components."""
    config = {
        "robot_ip": None,
        "agent_inputs": [{"type": "UnitreeGo2Odom", "name": "odom"}],
        "agent_actions": [{"type": "UnitreeGo2Move", "name": "move"}],
        "simulators": [{"type": "UnitreeGo2Sim", "name": "sim"}],
    }
    with pytest.raises(ValueError) as exc_info:
        _check_robot_config_requirements(config)
    
    error_msg = str(exc_info.value)
    assert "input" in error_msg
    assert "action" in error_msg
    assert "simulator" in error_msg


def test_robot_config_validation_accepts_whitespace_padded_ip():
    """Test that validation accepts robot_ip with surrounding whitespace."""
    config = {
        "robot_ip": "  192.168.1.100  ",
        "agent_inputs": [{"type": "UnitreeGo2Odom", "name": "odom"}],
    }
    # Should not raise
    _check_robot_config_requirements(config)
