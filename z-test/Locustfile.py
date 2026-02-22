import os
import time
import json
import random
import string
import threading
import itertools
import requests
import gevent

from locust import HttpUser, User, task, between, constant, events


# 0. 공통 유틸리티
def random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def http_to_ws(url: str) -> str:
    """http(s):// → ws(s):// 자동 변환"""
    return url.replace("https://", "wss://").replace("http://", "ws://")


# 1. 전역 유저 풀 (Thread-Safe)

USER_CREDENTIALS: list[dict] = []
_token_iter = None
_iter_lock = threading.Lock()


def get_next_credential() -> dict | None:
    """
    Thread-Safe하게 다음 자격증명 반환.
    on_test_start가 실패해서 _token_iter가 None이면 None을 반환.
    """
    if _token_iter is None:
        print("[get_next_credential] _token_iter가 None입니다. on_test_start 실패 여부를 확인하세요.")
        return None
    with _iter_lock:
        return next(_token_iter)


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """
    Locust 프로세스 시작 시 단 한 번 실행.
    START 클릭 전에 유저 풀을 미리 생성하여 Web UI 블로킹 방지.
    """
    global _token_iter

    base_url = environment.host or "http://localhost:8002"
    pool_size = int(os.getenv("LOCUST_POOL_SIZE", 100))

    # Nginx Rate Limit 우회: 유저 생성은 내부 서비스 직접 포트 사용
    # nginx.conf: upstream user_service { server user-service:8001; }
    # 외부(Nginx 80포트) → login_limit: 5r/m 으로 막힘
    # 내부(8001 직접)  → Rate Limit 없음
    
    auth_url = os.getenv("LOCUST_AUTH_URL", base_url)

    print(f"\n 테스트 준비: {pool_size}명의 더미 유저 풀 생성 중...")
    print(f"   테스트 서버: {base_url}")
    print(f"   인증 서버:   {auth_url}")
    if auth_url == base_url:
        print(f" LOCUST_AUTH_URL 미설정 → Nginx Rate Limit에 걸릴 수 있습니다.")
        print(f" 권장: LOCUST_AUTH_URL=http://localhost:8001 로 실행하세요.\n")

    # 서버 연결 사전 확인
    try:
        probe = requests.get(f"{base_url}/health", timeout=5)
        print(f" 테스트 서버 응답: HTTP {probe.status_code}")
    except Exception as e:
        print(f"\n 테스트 서버에 연결할 수 없습니다: {e}")
        print(f"  → 서버가 {base_url} 에서 실행 중인지 확인하세요.\n")
        return

    for i in range(pool_size):
        username = random_string()
        email = f"{username}@test.com"
        password = "test1234"

        try:
            # 회원가입 — auth_url (Nginx 우회 가능)
            reg = requests.post(
                f"{auth_url}/api/users/register",
                json={"email": email, "username": username, "password": password},
                timeout=10,
            )
            if reg.status_code not in (200, 201):
                if i == 0:
                    print(f" 첫 번째 유저 가입 실패 (status={reg.status_code})")
                    print(f" 응답 본문: {reg.text[:200]}")
                    if reg.status_code == 429:
                        print(f" Nginx Rate Limit 차단!")
                        print(f" LOCUST_AUTH_URL=http://localhost:8001 환경변수를 설정하세요.")
                continue

            # 로그인 — auth_url (Nginx 우회 가능)
            res = requests.post(
                f"{auth_url}/api/users/login",
                json={"email": email, "password": password},
                timeout=10,
            )
            if res.status_code == 200:
                data = res.json()
                token = data.get("access_token")
                user_id = data.get("user_id")

                if token and user_id:
                    USER_CREDENTIALS.append({"token": token, "user_id": user_id})
                else:
                    if i == 0:
                        print(f" 토큰/user_id 누락. 응답 키 확인: {list(data.keys())}")
            else:
                if i == 0:
                    print(f" 로그인 실패 (status={res.status_code})")
                    if res.status_code == 429:
                        print(f" Nginx Rate Limit 차단! LOCUST_AUTH_URL 설정 필요.")

        except Exception as e:
            print(f" 유저 [{i+1}] 생성 중 예외: {e}")

        # gevent 이벤트 루프에 제어권 양보 (Web UI 블로킹 방지)
        gevent.sleep(0)

    if not USER_CREDENTIALS:
        print("\n 유효한 유저가 한 명도 생성되지 않았습니다.")
        return

    _token_iter = itertools.cycle(USER_CREDENTIALS)
    print(f" 유저 풀 생성 완료! (총 {len(USER_CREDENTIALS)}명 / 요청 {pool_size}명)\n")


# 2. 시나리오 A: 순수 HTTP API 부하 (TPS 측정)
class HttpApiUser(HttpUser):
    """
    목적: REST API 엔드포인트의 TPS(초당 처리량)와 응답 시간 측정
    지표: RPS, 응답시간 P50/P95/P99, 에러율
    """
    # wait_time = constant(0)  # Spike 테스트 (대기 없이 연속 요청)
    wait_time = between(1, 3)  # 일반 부하 테스트 시 주석 해제

    def on_start(self):
        user_data = get_next_credential()
        # on_test_start 실패 시 해당 유저 안전하게 비활성화
        if user_data is None:
            self.token = None
            self.user_id = None
            self._headers = {}
            self.room_id = "room1"
            return
        self.token = user_data["token"]
        self.user_id = user_data["user_id"]
        self._headers = {"Authorization": f"Bearer {self.token}"}
        self.room_id = random.choice(["room1", "room2", "room3"])

    @task(3)
    def get_messages(self):
        """메시지 조회 (가중치 3 - 가장 빈번한 요청)"""
        if not self.token:
            return
        self.client.get(
            f"/api/chat/rooms/{self.room_id}/messages",
            headers=self._headers,
            name="HTTP_GET /rooms/[room_id]/messages",
        )

    @task(2)
    def get_online_users(self):
        """온라인 유저 조회 (가중치 2)"""
        if not self.token:
            return
        self.client.get(
            f"/api/chat/rooms/{self.room_id}/online",
            headers=self._headers,
            name="HTTP_GET /rooms/[room_id]/online",
        )

    @task(1)
    def get_notifications(self):
        """알림 조회 (가중치 1 - 가장 드문 요청)"""
        if not self.token:
            return
        self.client.get(
            f"/api/notify/{self.user_id}",
            headers=self._headers,
            name="HTTP_GET /notify/[user_id]",
        )


# 3. 시나리오 B: WebSocket 메시지 처리량 (RTT 측정)

class WsMessageUser(User):
    """
    목적: WebSocket 메시지 전송/수신의 RTT(왕복 지연시간) 측정
    지표: WS_Msg 응답시간 P50/P95/P99, 메시지 처리 TPS, 에러율
    """
    wait_time = constant(0)
    # wait_time = between(0.1, 0.5)  # 일반 부하 시 주석 해제

    def on_start(self):
        from websocket import create_connection

        user_data = get_next_credential()
        # on_test_start 실패 시 해당 유저 안전하게 비활성화
        if user_data is None:
            self.token = None
            self.ws = None
            return

        self.token = user_data["token"]
        self.ws = None

        ws_host = os.getenv(
            "LOCUST_WS_HOST",
            http_to_ws(self.environment.host or "ws://localhost:8002"),
        )

        start_conn = time.time()
        try:
            self.ws = create_connection(
                f"{ws_host}/api/chat/ws/room1?token={self.token}",
                timeout=10,
            )
            
            self.environment.events.request.fire(
                request_type="WS_Conn",
                name="Connect",
                response_time=(time.time() - start_conn) * 1000,
                response_length=0,
                exception=None,
            )
        except Exception as e:
            self.environment.events.request.fire(
                request_type="WS_Conn",
                name="Connect",
                response_time=(time.time() - start_conn) * 1000,
                response_length=0,
                exception=e,
            )
            
            self.ws = None

    @task
    def send_and_recv(self):
        """메시지 전송 → 에코/ACK 수신까지의 순수 RTT 측정"""
        if not self.ws or not self.ws.connected:
            return

        payload = json.dumps({"content": f"Load Test {random_string(4)}"})
        start = time.time()

        try:
            self.ws.send(payload)
            recv_msg = self.ws.recv()

            self.environment.events.request.fire(
                request_type="WS_Msg",
                name="Send_And_Recv_RTT",
                response_time=(time.time() - start) * 1000,
                response_length=len(recv_msg),
                exception=None,
            )
        except Exception as e:
            self.environment.events.request.fire(
                request_type="WS_Msg",
                name="Send_And_Recv_RTT",
                response_time=(time.time() - start) * 1000,
                response_length=0,
                exception=e,
            )
            # 연결이 끊긴 경우 소켓 상태 정리
            self.ws = None

    def on_stop(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass


# 4. 시나리오 C: WebSocket 동접 유지 한계 (Connection Limit)
class WsConnectionLimitUser(User):
    """
    목적: 서버가 버틸 수 있는 최대 동시 WebSocket 연결 수 측정
          (FD 고갈, 메모리 한계 탐색)
    지표: WS_Idle 연결 성공률, 연결 유지 중 에러율
    """
    wait_time = between(10, 20)  # 연결 유지만 하며 아무것도 안 하는 유저

    def on_start(self):
        from websocket import create_connection

        user_data = get_next_credential()
        # on_test_start 실패 시 해당 유저 안전하게 비활성화
        if user_data is None:
            self.ws = None
            return

        self.ws = None

        ws_host = os.getenv(
            "LOCUST_WS_HOST",
            http_to_ws(self.environment.host or "ws://localhost:8002"),
        )

        start = time.time()
        try:
            self.ws = create_connection(
                f"{ws_host}/api/chat/ws/room1?token={user_data['token']}",
                timeout=10,
            )
            self.environment.events.request.fire(
                request_type="WS_Idle",
                name="Maintain_Connection",
                response_time=(time.time() - start) * 1000,
                response_length=0,
                exception=None,
            )
        except Exception as e:
            self.environment.events.request.fire(
                request_type="WS_Idle",
                name="Maintain_Connection",
                response_time=(time.time() - start) * 1000,
                response_length=0,
                exception=e,
            )
            
            self.ws = None

    @task
    def heartbeat_check(self):
        if not self.ws:
            return
        try:
            self.ws.ping()
        except Exception as e:
            # ping 실패 = 연결 끊김 → 에러로 기록
            self.environment.events.request.fire(
                request_type="WS_Idle",
                name="Heartbeat_Ping",
                response_time=0,
                response_length=0,
                exception=e,
            )
            self.ws = None

    def on_stop(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass