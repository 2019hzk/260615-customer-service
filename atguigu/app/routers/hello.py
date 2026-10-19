from fastapi import APIRouter

router = APIRouter(tags=["测试路由"])


@router.get("/hello")
async def hello():
    return {"status": "ok"}  # FastAPI会自动完成序列化(将对象转换成字符串)
