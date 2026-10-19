"""
用户身份认证：
1. 是否携带令牌
2. 用户角色是哪一种
"""
import jwt
from fastapi import HTTPException, status

from atguigu.app.schemas import CurrentUser
from atguigu.common.settings import get_settings


def require_authorized_user(authorization: str | None, *roles: str) -> CurrentUser:
    # 1. 校验令牌 是否为空以及合法 401(未认证)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未携带有效令牌")

    # 2. 截取令牌
    access_token = authorization.split(" ", 1)[1]

    # 3. 根据令牌解密
    current_user = decode_token(access_token)
    if current_user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前用户无权访问")

    return current_user


def decode_token(access_token: str) -> CurrentUser:
    """
    职责：解析令牌获取用户信息
    jwt:加密、解密【加密算法、秘钥】
    :param access_token:
    :return:
    """

    user_info_dict = jwt.decode(access_token, key=get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])

    return CurrentUser.model_validate(user_info_dict)
