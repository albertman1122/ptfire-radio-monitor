# -*- coding: utf-8 -*-
"""
執行此腳本產生帳號密碼的 bcrypt hash，貼入 secrets.toml
用法：python gen_password.py
"""
import streamlit_authenticator as stauth

accounts = [
    ("admin",  "請輸入管理員密碼"),
    ("user1",  "請輸入使用者一密碼"),
]

print("=" * 60)
for username, pwd in accounts:
    hashed = stauth.Hasher([pwd]).generate()[0]
    print(f"\n帳號: {username}")
    print(f"密碼明文: {pwd}")
    print(f"bcrypt hash:\n{hashed}")
print("\n請將以上 hash 填入 secrets.toml 對應的 password 欄位")
print("=" * 60)
