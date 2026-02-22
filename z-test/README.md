# 📊 부하 테스트 (Locust)

## 사전 준비

```powershell
# 1. Docker 서비스 실행
cd e:\Folders\Eanston\chat-platform
docker compose --env-file .env.dev up --build

# 2. pip 패키지 설치 (최초 1회)
pip install locust websocket-client
```

>  부하 테스트 시 `gateway/nginx.conf`의 `rate=100r/m`을 `rate=10000r/m`으로 변경 후, 테스트 완료 시 반드시 복원하세요.

---

## 시나리오 A: HTTP API 부하 (TPS 측정)

```powershell
# 일반 부하 테스트
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py HttpApiUser --host http://localhost:80

# 시간 제한 (2분)
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py HttpApiUser --host http://localhost:80 --run-time 2m

# headless 모드 (UI 없이 CLI에서 직접 결과 확인)
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py HttpApiUser --host http://localhost:80 --headless -u 50 -r 10 --run-time 2m
```

**측정 지표**: RPS, 응답시간 P50/P95/P99, 에러율

---

## 시나리오 B: WebSocket 메시지 RTT

```powershell
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py WsMessageUser --host http://localhost:80

# 시간 제한 (2분)
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py WsMessageUser --host http://localhost:80 --run-time 2m

# headless 모드
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py WsMessageUser --host http://localhost:80 --headless -u 50 -r 10 --run-time 2m
```

**측정 지표**: WS_Msg 응답시간 P50/P95/P99, 메시지 처리 TPS

---

## 시나리오 C: WebSocket 동접 한계

```powershell
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py WsConnectionLimitUser --host http://localhost:80

# 시간 제한 (2분)
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py WsConnectionLimitUser --host http://localhost:80 --run-time 2m

# headless 모드 (점진적 증가)
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py WsConnectionLimitUser --host http://localhost:80 --headless -u 500 -r 10 --run-time 5m
```

**측정 지표**: 최대 동시 연결 수, 연결 성공률, Heartbeat 에러율

---

## 전체 시나리오 동시 실행 (혼합 부하)

```powershell
$env:LOCUST_AUTH_URL="http://localhost:8001"; locust -f locustfile.py --host http://localhost:80
```

---

## Locust Web UI

- **URL**: http://localhost:8089
- **Number of users**: 동시 접속 유저 수
- **Ramp up**: 초당 추가되는 유저 수
- START 클릭 후 **1분 대기 → 브라우저 새로고침(F5)** 하면 결과 표시

---

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `LOCUST_AUTH_URL` | (host와 동일) | 유저 생성/로그인 서버 (Rate Limit 우회용) |
| `LOCUST_POOL_SIZE` | `100` | 사전 생성할 더미 유저 수 |
| `LOCUST_WS_HOST` | (host 기반 자동) | WebSocket 서버 주소 |

---

## 테스트 후 정리

```powershell
# DB에서 테스트 유저 삭제 (Supabase SQL Editor)
DELETE FROM "Users" WHERE id != 1;
```
