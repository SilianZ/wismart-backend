import smtplib, ssl, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

smtp_server = os.getenv("SMTP_SERVER") or ""
sender_email = os.getenv("SMTP_EMAIL") or ""
sender_password = os.getenv("SMTP_PASSWORD") or ""


def send_verification_email(email: str, username: str, token: str) -> None:
    with smtplib.SMTP_SSL(
        smtp_server, 465, context=ssl.create_default_context()
    ) as server:
        server.login(sender_email, sender_password)
        message = MIMEMultipart("alternative")
        message["Subject"] = "[WisMart] 邮箱验证"
        message["From"] = f"WisMart <{sender_email}>"
        message["To"] = email
        mail_body = f"""
        <!DOCTYPE html>
        <html xmlns="http://www.w3.org/1999/xhtml">
        <body>
        <tbody>
        <tr>
            <td align="center" valign="top">
            <table class="container" align="center" width="640" cellpadding="0" cellspacing="0" border="0"
                style="max-width: 640px;">
                <tbody>
                <tr>
                    <td colspan="2" height="20"></td>
                </tr>
                <tr>
                    <td align="center">
                    <img src="https://www.hfiuc.org/icon512_rounded.png"
                        alt="" width="111" class="logo" style="max-width: 111px; display: inline-block;">
                    </td>
                </tr>
                </tbody>
            </table>

            <table class="container ml-default-border" width="640" align="center" bgcolor="#ffffff" border="0"
                cellspacing="0" cellpadding="0" style="width: 640px; min-width: 640px;">
                <tbody>
                <tr>
                    <td height="20"></td>
                </tr>
                <tr>
                    <td align="center">
                    <h4
                        style="font-family: 'Inter', sans-serif; color: #f86238; font-size: 16px; font-weight: bold; text-align: center;">
                        嘿，{username}！</h4>
                    <h1
                        style="font-family: 'Inter', sans-serif; color: #000000; font-size: 28px; font-weight: bold; text-align: center;">
                        邮箱验证</h1>
                    </td>
                </tr>
                </tbody>
            </table>

            <table class="container ml-default-border" width="640" bgcolor="#ffffff" align="center" border="0"
                cellspacing="0" cellpadding="0" style="width: 640px; min-width: 640px;">
                <tbody>
                <tr>
                    <td height="20"></td>
                </tr>
                <tr>
                    <td align="center" style="padding: 0 50px;">
                    <p
                        style="font-family: 'Inter', sans-serif; color: #6B7280; font-size: 16px; line-height: 165%;">
                        你现在正在为 WisMart 用户&nbsp;<strong>{username}</strong>&nbsp;进行邮箱验证。
                    </p>
                    </td>
                </tr>
                <tr>
                    <td height="10"></td>
                </tr>
                </tbody>
            </table>

            <table class="container ml-default-border" width="640" bgcolor="#ffffff" align="center" border="0"
                cellspacing="0" cellpadding="0" style="width: 640px; min-width: 640px;">
                <tbody>
                <tr>
                    <td align="center"
                    style="padding: 40px; border: 1px solid #E6E6E6; border-radius: 7px; background-color: #FCFCFC;">
                    <p
                        style="font-family: 'Inter', sans-serif; color: #6B7280; font-size: 16px; line-height: 165%;">
                        点击以下按钮完成验证。该验证邮件的有效期为 5 分钟。</p>
                    <table class="ml-btn-container" cellpadding="0" cellspacing="0" border="0" align="center">
                        <tbody>
                        <tr>
                            <td align="center">
                            <a target="_blank" href="http://wismart.hfiuc.org/user/verify?token={token}"
                                style="display: block; padding: 14px 25px; background-color: #fd7e14; color: #ffffff; font-family: 'Inter', sans-serif; font-size: 16px; text-decoration: none; border-radius: 30px;">
                                验证
                            </a>
                            </td>
                        </tr>
                        </tbody>
                    </table>
                    </td>
                </tr>
                </tbody>
            </table>

            <table class="container ml-default-border" width="640" bgcolor="#ffffff" align="center" border="0"
                cellspacing="0" cellpadding="0" style="width: 640px; min-width: 640px;">
                <tbody>
                <tr>
                    <td height="20"></td>
                </tr>
                <tr>
                    <td align="center" style="padding: 0 50px;">
                    <p
                        style="font-family: 'Inter', sans-serif; color: #6B7280; font-size: 16px; line-height: 165%;">
                        如果你对这条消息感到陌生，请忽略。
                    </p>
                    </td>
                </tr>
                <tr>
                    <td height="20"></td>
                </tr>
                </tbody>
            </table>

            <table class="container ml-default-border" width="640" bgcolor="#fd7e14" align="center" border="0"
                cellspacing="0" cellpadding="0" style="width: 640px; min-width: 640px;">
                <tbody>
                <tr>
                    <td height="10"></td>
                </tr>
                <tr>
                    <td align="center">
                    <p
                        style="font-family: 'Inter', sans-serif; color: #ffffff; font-size: 14px; line-height: 150%;">
                        © 2025 WisMart & MAKERs'。保留所有权利。
                    </p>
                    </td>
                </tr>
                <tr>
                    <td height="10"></td>
                </tr>
                </tbody>
            </table>
            </td>
        </tr>
        </tbody>
        </body>
        </html>
        """

        part = MIMEText(mail_body, "html", "utf-8")
        message.attach(part)
        server.sendmail(sender_email, email, message.as_string())
