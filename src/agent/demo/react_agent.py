import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from src.common.setting import settings

load_dotenv(override=True)
model = settings.openai_model

question = "no_thinking 你是谁"

for chunk in model.stream(question):
    # stream print 参数end=""表示不换行，flush=True表示立即刷新
    print(chunk.content,end="",flush=True)
