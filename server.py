"""
FastAPI 接口：取邮件
启动：
  pip install fastapi uvicorn opencv-python numpy captcha-recognizer
  python server.py  # 默认 0.0.0.0:8000

调用：
  POST /mails
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import requests
import re


class EmailRequest(BaseModel):
    email: str
    time: int = 30
    subject: str


class EmailResponse(BaseModel):
    code: int
    email: str


class MailSession:
    """邮件会话：管理认证状态和请求"""

    BASE_URL = "https://www.2925.com"

    def __init__(self):
        self.cookie = self._load_cookie()
        self.token = None
        self.refresh_token()  # 初始化时立即获取 token

    def _load_cookie(self):
        with open("cookie.txt", "r", encoding="utf-8") as f:
            return f.read().strip()

    def _build_headers(self, with_auth=False):
        headers = {
            "Host": "www.2925.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Cookie": self.cookie,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def refresh_token(self):
        """获取新 token"""
        url = f"{self.BASE_URL}/mailv2/auth/token"
        res = requests.post(url, json={"timeout": 5000}, headers=self._build_headers())
        data = res.json()
        if data.get("code") == 200:
            self.token = data["result"]
            return True
        return False

    def get_mail_list(self):
        """获取邮件列表，401 时自动刷新 token 重试一次"""
        url = f"{self.BASE_URL}/mailv2/maildata/MailList/mails?Folder=Inbox&FilterType=0&PageIndex=1&PageCount=25"
        res = requests.get(url, headers=self._build_headers(with_auth=True))
        data = res.json()

        # 401 说明 token 过期，用 cookie 重新获取 token
        if data.get("status_code") == 401:
            if not self.refresh_token():
                raise HTTPException(status_code=401, detail="cookie 过期，无法获取新 token")
            # token 刷新成功，重新请求
            res = requests.get(url, headers=self._build_headers(with_auth=True))
            data = res.json()

        return data.get("result", {}).get("list", []) if data.get("code") == 200 else []

    def read_mail(self, message_id):
        """读取邮件内容"""
        url = f"{self.BASE_URL}/mailv2/maildata/MailRead/mails/read"
        params = {"MessageID": message_id, "FolderName": "Inbox", "IsPre": "false"}
        res = requests.get(url, params=params, headers=self._build_headers())
        data = res.json()

        if data.get("code") == 200:
            html = data["result"]["bodyHtmlText"]
            return re.sub(r'<[^>]*>', '', html)
        return None


app = FastAPI(title="Get 2925 email", version="1.0.0")
mail_session = MailSession()


@app.post("/mails", response_model=EmailResponse)
def getmails(req: EmailRequest):
    """获取符合条件的邮件"""
    mail_list = mail_session.get_mail_list()
    current_time_ms = time.time() * 1000
    time_threshold_ms = req.time * 1000

    for mail in mail_list:
        mail_age = current_time_ms - float(mail["createTime"])
        if (mail_age < time_threshold_ms and
            mail["toAddress"][0] == req.email and
            mail["subject"] == req.subject):

            content = mail_session.read_mail(mail["messageId"])
            if content:
                return EmailResponse(code=200, email=content)

    return EmailResponse(code=0, email="")


if __name__ == "__main__":
    print(f"Token: {mail_session.token}")