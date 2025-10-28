"""
FastAPI 接口：取邮件
启动：
  pip install fastapi uvicorn opencv-python numpy captcha-recognizer beautifulsoup4
  python server.py  # 默认 0.0.0.0:8000

调用：
  POST /mails
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import requests
import re
import json
from bs4 import BeautifulSoup


from typing import Optional

class EmailRequest(BaseModel):
    email: str
    time: int = 30
    subject: Optional[str] = ""
    bodyContent: Optional[str] = ""


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
            "Cookie": self.cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "origin": "https://www.2925.com",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://www.2925.com/",
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "priority": "u=1, i",
        }
        if with_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def refresh_token(self):
        """获取新 token"""
        url = f"{self.BASE_URL}/mailv2/auth/token"
        res = requests.post(
            url, data=json.dumps({"timeout": 5000}), headers=self._build_headers()
        )
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
                raise HTTPException(
                    status_code=401, detail="cookie 过期，无法获取新 token"
                )
            # token 刷新成功，重新请求
            res = requests.get(url, headers=self._build_headers(with_auth=True))
            data = res.json()

        return data.get("result", {}).get("list", []) if data.get("code") == 200 else []

    def read_mail(self, message_id):
        """读取邮件内容"""
        url = f"{self.BASE_URL}/mailv2/maildata/MailRead/mails/read"
        params = {"MessageID": message_id, "FolderName": "Inbox", "IsPre": "false"}
        res = requests.get(url, params=params, headers=self._build_headers(True))
        data = res.json()

        if data.get("code") == 200:
            html = data["result"]["bodyHtmlText"]
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(strip=True)
        return None


app = FastAPI(title="Get 2925 email", version="1.0.0")
mail_session = MailSession()


@app.post("/mails", response_model=EmailResponse)
def getmails(req: EmailRequest):
    """获取符合条件的邮件"""
    mail_list = mail_session.get_mail_list()
    current_time_ms = time.time() * 1000
    time_threshold_ms = req.time * 1000
    subject = req.subject
    bodyContent = req.bodyContent
    for mail in mail_list:
        mail_age = current_time_ms - float(mail["createTime"])
        if (
            mail_age < time_threshold_ms
            and mail["toAddress"][0] == req.email
            and (
                (bodyContent and bodyContent in mail["bodyContent"])
                or mail["subject"] == subject
            )
        ):
            content = mail_session.read_mail(mail["messageId"])
            if content:
                return EmailResponse(code=200, email=content)

    return EmailResponse(code=0, email="")


if __name__ == "__main__":
    import uvicorn
    print(f"Token: {mail_session.token}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
