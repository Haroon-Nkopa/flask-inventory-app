import logging
from logging.handlers import SMTPHandler
from unittest.mock import MagicMock, patch
import pytest
from flask import Flask
from app.sending_email import send_error_email

@pytest.fixture
def mock_app():
    """Creates a mock Flask app with the required mail configuration."""
    app = Flask(__name__)
    app.config['MAIL_SERVER'] = 'smtp.example.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USERNAME'] = 'test-user'
    app.config['MAIL_PASSWORD'] = 'test-password'
    app.config['MAIL_USE_TLS'] = True
    app.config['ADMINS'] = ['admin@example.com']
    
    yield app
    
    # Clean up handlers after each test run to prevent global state leaks
    app.logger.handlers.clear()

def test_send_error_email_attaches_handler(mock_app):
    """Verifies that SMTPHandler is correctly initialized and attached to the logger."""
    
    # Patch SMTPHandler specifically inside the context manager scope
    with patch('app.sending_email.SMTPHandler') as MockSMTPHandler:
        mock_handler_instance = MagicMock()
        MockSMTPHandler.return_value = mock_handler_instance
        
        send_error_email(mock_app)
        
        # 1. Assert SMTPHandler was instantiated with the right config parameters
        MockSMTPHandler.assert_called_once_with(
            mailhost=('smtp.example.com', 587),
            fromaddr='no-reply@smtp.example.com',
            toaddrs=['admin@example.com'],
            subject='Flask Inventory App Failure',
            credentials=('test-user', 'test-password'),
            secure=()
        )
        
        # 2. Assert the handler log level was set to ERROR
        mock_handler_instance.setLevel.assert_called_once_with(logging.ERROR)
        
        # 3. Assert the handler was actually appended to the app's logger components
        assert any(h == mock_handler_instance for h in mock_app.logger.handlers)

def test_send_error_email_skips_without_mail_server():
    """Ensures no handler is attached if MAIL_SERVER is missing or empty."""
    app = Flask(__name__)
    app.config['MAIL_SERVER'] = None  # No server configured
    app.config['ADMINS'] = ['admin@example.com']
    
    # Safely ensure the handler array is empty
    app.logger.handlers.clear()
    
    send_error_email(app)
    
    # Assert no logging handlers were added
    assert len(app.logger.handlers) == 0
    
    # Final cleanup
    app.logger.handlers.clear()
