import redis.asyncio as redis

redis_client = redis.Redis(host='192.168.200.199', port=6379, db=0, decode_responses=True)
