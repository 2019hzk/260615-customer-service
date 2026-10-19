from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atguigu.common.settings import get_settings

from atguigu.app.routers import hello

from atguigu.app.routers import chat

# 标准导入顺序：
# 1. 导入sdk自带的

# 2. 导入第三方的

# 3. 导入自己定义

app = FastAPI()

app.include_router(hello.router)
app.include_router(chat.router)

# 添加跨域（浏览器处于对资源访问的安全做的一种限制：同源请求）
app.add_middleware(CORSMiddleware,
                   allow_origins=get_settings().cors_origins,
                   allow_credentials=True,  # 可以带一些认证信息【cookie[user_id:xxxx]   header[Authorization: Bear xxxxxx]】
                   allow_methods=["*"],  # get post   put delete...
                   allow_headers=["*"],  # 请求头中可以放任意的key value
                   )
