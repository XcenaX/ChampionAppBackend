from typing import Optional, List, Dict
import json
from redis import Redis

# Простой класс для использования redis
# При необходимости доделать
class RedisCallService:

    def __init__(self, redis_conn: Redis) -> None:
        self.redis_conn = redis_conn

    def put_some_data(
        self,
        data_id: Optional[int],
        data_name: List[int],
        more_data: List[str],
        even_more_data: Optional[int] = None
    ) -> None:
        call_data = {
            'data_name': data_name,
            'more_data': more_data,
            'even_more_data': even_more_data
        }
        call_data = json.dumps(call_data)
        self.redis_conn.set(str(data_id), call_data)

    def get_call_data_by_call_id(self, call_id: int) -> Optional[Dict]:
        try:
            string_data = self.redis_conn.get(call_id)
            data = json.loads(string_data)
        except:
            return None
        return data

    def delete_call_data_by_call_id(self, call_id: int) -> None:
        self.redis_conn.delete(str(call_id))