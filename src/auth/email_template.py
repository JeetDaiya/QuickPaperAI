def render_otp_email(otp_code: str) -> str:
    """Renders HTML content for OTP verification email."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f5; padding: 20px; color: #18181b; }}
            .card {{ max-width: 480px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #e4e4e7; }}
            .title {{ font-size: 20px; font-weight: 700; color: #09090b; margin-bottom: 8px; text-align: center; }}
            .subtitle {{ font-size: 14px; color: #71717a; text-align: center; margin-bottom: 24px; }}
            .otp-box {{ background-color: #f4f4f5; border: 1px dashed #a1a1aa; border-radius: 8px; padding: 16px; text-align: center; font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #e11d48; margin: 20px 0; }}
            .footer {{ font-size: 12px; color: #a1a1aa; text-align: center; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="title">QuickPaper AI</div>
            <div class="subtitle">Verification Code</div>
            <p style="font-size: 14px; color: #3f3f46;">Use the verification code below to complete your authentication process. This code will expire in 10 minutes.</p>
            <div class="otp-box">{otp_code}</div>
            <p style="font-size: 13px; color: #71717a;">If you did not request this code, you can safely ignore this email.</p>
            <div class="footer">&copy; QuickPaper AI. All rights reserved.</div>
        </div>
    </body>
    </html>
    """
