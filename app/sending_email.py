import os
import logging
import resend

# 1. Create a custom logging handler for Resend
class ResendCustomLogsHandler(logging.Handler):
    def __init__(self, to_email, from_email="onboarding@resend.dev"):
        super().__init__()
        self.to_email = to_email
        self.from_email = from_email
        # Initialize the API key securely
        resend.api_key = os.environ.get("RESEND_API_KEY")

    def emit(self, record):
        try:
            # Format the error log message into readable text
            log_entry = self.format(record)
            
            # Send the error alert via Resend HTTPS API
            resend.Emails.send({
                "from": self.from_email,
                "to": self.to_email,
                "subject": f"Flask Inventory App Failure: {record.levelname}",
                "html": f"<pre>{log_entry}</pre>"
            })
        except Exception as e:
            # Fallback to avoid infinite loops if logging itself fails
            print(f"Failed to send log via Resend: {str(e)}")

# 2. Update your setup function
def send_error_email(app):
    # Only configure error mailing if we have a valid Resend API key and admins set up
    if os.environ.get("RESEND_API_KEY") and app.config.get('ADMINS'):
        
        # Grab the first administrator email from your config array
        admin_email = app.config['ADMINS'][0]

        # Use onboarding@resend.dev unless you have verified a custom domain
        from_email = "onboarding@resend.dev" 

        # Create our custom handler instance
        mail_handler = ResendCustomLogsHandler(to_email=admin_email, from_email=from_email)
        
        # Set it to only trigger on system errors and crashes
        mail_handler.setLevel(logging.ERROR)
        
        # Format how the log entries look in the email body
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        mail_handler.setFormatter(formatter)
        
        # Attach the handler to the Flask application logger
        app.logger.addHandler(mail_handler)
