def render_otp_email(otp_code : str) -> str:
    html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
                <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Verification Code &mdash; QuickPaperAI</title>
                </head>
                <body style="margin: 0; padding: 0; background-color: #f3f1eb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; width: 100% !important;">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f3f1eb; padding: 40px 10px;">
                    <tr>
                    <td align="center">
                        <!-- Main Email Container -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 540px; background-color: #faf8f5; border: 1px solid #e2ded5; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); overflow: hidden;">

                        <!-- Vermillion Top Accent Line -->
                        <tr>
                            <td height="4" style="background-color: #d34e36; line-height: 4px; font-size: 4px;">&nbsp;</td>
                        </tr>

                        <!-- Header (Brand Name & Monospace Stamp Label) -->
                        <tr>
                            <td style="padding: 35px 40px 20px 40px; border-bottom: 1px dashed #e2ded5;">
                            <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                <td>
                                    <span style="font-family: Georgia, serif; font-size: 22px; font-style: italic; font-weight: bold; color: #161b22; letter-spacing: -0.5px;">QuickPaperAI</span>
                                </td>
                                <td align="right">
                                    <span style="font-family: 'Courier New', Courier, monospace; font-size: 10px; font-weight: bold; text-transform: uppercase; color: #d34e36; letter-spacing: 2px; border: 1px solid #d34e36; padding: 2px 6px; border-radius: 2px;">OTP PASS</span>
                                </td>
                                </tr>
                            </table>
                            </td>
                        </tr>

                        <!-- Content Body -->
                        <tr>
                            <td style="padding: 40px 40px 30px 40px;">
                            <p style="margin: 0 0 10px 0; font-family: 'Courier New', Courier, monospace; font-size: 11px; font-weight: bold; text-transform: uppercase; color: #737880; letter-spacing: 3px;">
                                01 &mdash; Security Verification
                            </p>
                            <h1 style="margin: 0 0 20px 0; font-family: Georgia, serif; font-size: 28px; font-weight: normal; line-height: 1.2; color: #161b22;">
                                Confirm your identity
                            </h1>
                            <p style="margin: 0 0 30px 0; font-size: 15px; line-height: 1.6; color: #4a4d52;">
                                A sign-in attempt was initiated for your QuickPaperAI account. Use the verification code below to authorize access to your Examiner's Desk.
                            </p>

                            <!-- OTP Box Section -->
                            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fcfbfa; border: 1px solid #e8e5dc; border-radius: 3px; margin: 30px 0;">
                                <tr>
                                <td align="center" style="padding: 25px 20px;">
                                    <div style="font-family: 'Courier New', Courier, monospace; font-size: 38px; font-weight: bold; letter-spacing: 8px; color: #161b22; line-height: 1.1;">
                                    {otp_code}
                                    </div>
                                    <div style="margin-top: 10px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 11px; color: #d34e36; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 500;">
                                    Code expires in 10 minutes
                                    </div>
                                </td>
                                </tr>
                            </table>

                            <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #737880;">
                                If you did not make this request, please ignore this email or contact support if you suspect unauthorized activity.
                            </p>
                            </td>
                        </tr>

                        <!-- Footer Details -->
                        <tr>
                            <td style="padding: 25px 40px 35px 40px; background-color: #f7f5ef; border-top: 1px solid #e2ded5;">
                            <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                <td style="font-family: 'Courier New', Courier, monospace; font-size: 10px; color: #737880; line-height: 1.6; text-transform: uppercase; letter-spacing: 1.5px;">
                                    QuickPaperAI Desk System<br>
                                    Syllabus Presets &bull; AI Grading<br>
                                    <span style="color: #a0a4a8;">Protected under secure key session</span>
                                </td>
                                <td align="right" valign="bottom" style="font-family: 'Courier New', Courier, monospace; font-size: 10px; color: #a0a4a8; text-transform: uppercase; letter-spacing: 1.5px;">
                                    &copy; 2026
                                </td>
                                </tr>
                            </table>
                            </td>
                        </tr>
                        </table>
                    </td>
                    </tr>
                </table>
                </body>
            </html>
        """
    return  html_content