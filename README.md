# 실시간 채팅 플랫폼

MSA 기반 실시간 채팅 백엔드 시스템.  
FastAPI + WebSocket + Kafka + Redis + Docker 기반 대용량 트래픽 처리 구조.

---

## 아키텍처

```
클라이언트 → Nginx Gateway (:80)
               ├─ /api/users/*    → user-service (:8001)    [PostgreSQL]
               ├─ /api/chat/*     → chat-service (:8002)    [MongoDB, Kafka]
               └─ /api/notify/*   → notification-service (:8003)  [Kafka Consumer]
                                         ↕
                                      [Redis] 캐시 / 세션 / 온라인 상태 / 알림
```

---

## 기술 스택

| 분류 | 기술 |
|---|---|
| 프레임워크 | FastAPI (비동기) |
| 실시간 통신 | WebSocket |
| 메시지 브로커 | Apache Kafka |
| 캐시 / 세션 | Redis |
| 유저 DB | PostgreSQL + SQLAlchemy (asyncpg) |
| 메시지 DB | MongoDB + Motor |
| 인증 | JWT + bcrypt |
| 게이트웨이 | Nginx (Rate Limiting, Load Balancing) |
| 컨테이너 | Docker + Docker Compose |
| 런타임 | Python 3.11 |

---

## 서비스 구성

| 서비스 | 역할 | 주요 기술 |
|---|---|---|
| **user-service** | 회원가입, 로그인, JWT 인증, 유저 조회 | PostgreSQL, Redis 캐시 |
| **chat-service** | WebSocket 채팅, 메시지 저장/조회 | MongoDB, Kafka Producer, Redis |
| **notification-service** | 오프라인 유저 알림 저장/조회 | Kafka Consumer, Redis |

---

## 서버 구동

### 사전 요구사항

- Docker Desktop
- Git

### 실행

```bash
git clone https://github.com/your-username/chat-platform.git
cd chat-platform
cp .env.example .env    # 환경변수 설정
docker compose up --build
```

### 실행 확인

| 서비스 | URL |
|---|---|
| Gateway | http://localhost/health |
| User Service | http://localhost/api/users/health |
| Chat Service | http://localhost/api/chat/health |
| Notification | http://localhost/api/notify/health |

### 개별 실행 (개발용)

```bash
# 인프라만 실행
docker compose up redis kafka zookeeper

# 서비스 단독 실행 (예: user-service)
cd services/user-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

---

## API 엔드포인트

### User Service `/api/users`

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/register` | 회원가입 |
| POST | `/login` | 로그인 (JWT 발급) |
| GET | `/{user_id}` | 유저 조회 (Redis 캐시) |

### Chat Service `/api/chat`

| Method | Endpoint | 설명 |
|---|---|---|
| WS | `/ws/{room_id}?token={JWT}` | WebSocket 채팅 연결 |
| GET | `/rooms/{room_id}/messages?before=&limit=50` | 이전 메시지 조회 (커서 페이지네이션) |
| GET | `/rooms/{room_id}/online` | 온라인 유저 목록 |

### Notification Service `/api/notify`

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/{user_id}` | 알림 목록 + 읽지 않은 수 |
| POST | `/{user_id}/read` | 전체 읽음 처리 |

---

## 주요 설계 포인트

- **전 구간 비동기 I/O** — FastAPI + asyncpg + Motor + aiokafka
- **이벤트 기반 통신** — Kafka로 서비스 간 결합도 제거
- **Redis 다층 캐싱** — 유저 프로필, 최근 메시지, 온라인 상태
- **커서 기반 페이지네이션** — 대용량 메시지 조회 성능 확보
- **분산 환경 대응** — Redis 온라인 상태 공유, Kafka Consumer Group
- **보안** — bcrypt 해싱, JWT 인증, Nginx Rate Limiting

---

## 문서

상세 API 명세, 인프라 설정, 설계 문서는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)를 참고하세요.

---

## License

MIT
