import os
import logging
from unittest.mock import MagicMock, patch
import pytest
from flask import Flask
from app.sending_email import send_error_email, ResendCustomLogsHandler

@pytest.fixture
def mock_app():
    """Creates a mock Flask app with the updated Resend mail configuration."""
    app = Flask(__name__)
    # The config now holds a list of admin emails
    app.config['ADMINS'] = ['admin@example.com']
    
    yield app
    
    # Clean up handlers after each test run to prevent global state leaks
    app.logger.handlers.clear()

@patch.dict(os.environ, {"RESEND_API_KEY": "re_mock_test_key_12345"})
def test_send_error_email_attaches_resend_handler(mock_app):
    """Verifies that ResendCustomLogsHandler is initialized and attached to the logger."""
    
    # Patch our new custom handler inside the module scope
    with patch('app.sending_email.ResendCustomLogsHandler') as MockResendHandler:
        mock_handler_instance = MagicMock()
        MockResendHandler.return_value = mock_handler_instance
        
        send_error_email(mock_app)
        
        # 1. Assert the handler was instantiated with the correct arguments from config
        MockResendHandler.assert_called_once_with(
            to_email='admin@example.com',  # FIX: Change from list to plain string
            from_email='onboarding@resend.dev'
        )

        
        # 2. Assert the handler log level was constrained strictly to ERROR
        mock_handler_instance.setLevel.assert_called_once_with(logging.ERROR)
        
        # 3. Assert the custom formatter was applied to the handler instance
        mock_handler_instance.setFormatter.assert_called_once()
        
        # 4. Assert the handler was successfully appended to the app's logger core
        assert any(h == mock_handler_instance for h in mock_app.logger.handlers)

@patch.dict(os.environ, {}, clear=True)
def test_send_error_email_skips_without_api_key(mock_app):
    """Ensures no handler is attached if the RESEND_API_KEY environment variable is missing."""
    # Ensure handlers are starting fresh
    mock_app.logger.handlers.clear()
    
    send_error_email(mock_app)
    
    # Assert no logging handlers were added because the API key is completely absent
    assert len(mock_app.logger.handlers) == 0
