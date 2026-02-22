# 실시간 채팅 플랫폼

MSA(마이크로서비스 아키텍처) 기반 **실시간 채팅 백엔드 시스템**입니다.  
FastAPI + WebSocket + Kafka + Redis + Docker를 활용한 대용량 트래픽 처리 구조를 구현합니다.

---

## 시스템 아키텍처

```
                           ┌──────────────────────────────────────────────────┐
                           │              Docker Compose 환경                 │
                           │                                                  │
  클라이언트 ──────────▶   │   ┌────────────────────────────────────┐         │
  (웹 / 모바일 / API)       │   │     Nginx Gateway (:80)            │         │
                           │   │                                    │         │
                           │   │  • Rate Limiting (100r/m, 5r/m)   │         │
                           │   │  • WebSocket Proxy (1h timeout)   │         │
                           │   │  • Upstream Load Balancing        │         │
                           │   └───────┬──────────┬──────────┬─────┘         │
                           │           │          │          │                │
                           │    ┌──────▼───┐ ┌───▼────┐ ┌───▼──────────┐    │
                           │    │  User     │ │  Chat  │ │ Notification │    │
                           │    │  Service  │ │ Service│ │   Service    │    │
                           │    │  :8001    │ │ :8002  │ │    :8003     │    │
                           │    └──┬───┬───┘ └┬──┬──┬─┘ └──┬─────┬────┘    │
                           │       │   │      │  │  │      │     │         │
                           │  ┌────▼┐ ┌▼────┐ │ ┌▼──▼──┐  ┌▼─────▼──┐     │
                           │  │Postgre│ │Redis│ │ │Kafka │  │  Redis  │     │
                           │  │ SQL  │ │     │ │ │      │  │         │     │
                           │  └──────┘ └─────┘ │ └──────┘  └─────────┘     │
                           │               ┌───▼────┐                       │
                           │               │MongoDB │                       │
                           │               └────────┘                       │
                           └──────────────────────────────────────────────────┘
```

### 서비스 간 통신 흐름

```
유저A → WebSocket 메시지 전송
    │
    ▼
chat-service
    ├── 1. MongoDB 영구 저장
    ├── 2. WebSocket broadcast (같은 방 온라인 유저 즉시 수신)
    ├── 3. Kafka "chat-messages" 토픽에 이벤트 발행
    └── 4. Redis 캐시 (최근 30개 메시지, TTL 1시간)
              │
              ▼
notification-service (Kafka Consumer)
    ├── 온라인 유저  → skip (이미 WebSocket으로 수신)
    └── 오프라인 유저 → Redis에 알림 저장 (다음 접속 시 수신)
```

---

## 기술 스택

| 분류 | 기술 | 용도 |
|---|---|---|
| 웹 프레임워크 | FastAPI 0.109 | 비동기 REST API + WebSocket |
| 실시간 통신 | WebSocket | 양방향 실시간 메시지 |
| 메시지 브로커 | Apache Kafka 7.4.0 | 서비스 간 이벤트 스트리밍 |
| 캐시 / 세션 | Redis 7 | 유저 캐시, 메시지 캐시, 온라인 상태, 알림 저장 |
| 유저 DB | PostgreSQL + asyncpg | 유저 정형 데이터 (비동기 I/O) |
| 메시지 DB | MongoDB + Motor 3.3 | 메시지 비정형 데이터 (비동기 I/O) |
| ORM | SQLAlchemy 2.0 (비동기) | PostgreSQL 모델/쿼리 매핑 |
| API 게이트웨이 | Nginx | 리버스 프록시, Rate Limiting, 로드밸런싱 |
| 인증 | JWT (python-jose) + bcrypt | 토큰 기반 인증 |
| 컨테이너 | Docker + Docker Compose | 멀티 서비스 오케스트레이션 |
| 런타임 | Python 3.11 | 모든 서비스 공통 |

---

## 프로젝트 구조

```
chat-platform/
├── .env.example                 # 환경변수 템플릿
├── docker-compose.yml           # 전체 서비스 오케스트레이션
│
├── gateway/
│   └── nginx.conf               # Nginx 게이트웨이 설정
│       ├── Rate Limiting 정의 (api_limit, login_limit)
│       ├── upstream 로드밸런싱 (스케일 아웃 대비)
│       └── WebSocket 프록시 설정 (Upgrade 헤더)
│
└── services/
    ├── user-service/              # 회원가입, 로그인, JWT 인증
    │   ├── core/
    │   │   ├── config.py          # 환경변수 (DB, Redis, JWT 설정)
    │   │   ├── database.py        # PostgreSQL 비동기 커넥션 풀
    │   │   └── redis_client.py    # Redis 비동기 클라이언트
    │   ├── models/user.py         # SQLAlchemy User 모델
    │   ├── schemas/user.py        # Pydantic 요청/응답 스키마
    │   ├── repositories/user_repo.py  # DB CRUD 레이어
    │   ├── services/user_service.py   # 비즈니스 로직 + 캐싱
    │   ├── routers/user_router.py     # API 엔드포인트 정의
    │   ├── requirements.txt
    │   ├── Dockerfile
    │   └── main.py                # FastAPI 앱 엔트리포인트
    │
    ├── chat-service/              # WebSocket 실시간 메시지 처리
    │   ├── core/
    │   │   ├── config.py          # 환경변수 (MongoDB, Redis, Kafka, JWT)
    │   │   ├── auth.py            # WebSocket JWT 토큰 검증
    │   │   ├── mongo_client.py    # MongoDB 클라이언트 + 인덱스 초기화
    │   │   ├── redis_client.py    # Redis 비동기 클라이언트
    │   │   └── kafka_client.py    # Kafka Producer (재시도 로직 포함)
    │   ├── models/message.py      # Pydantic 메시지 도큐먼트 모델
    │   ├── schemas/chat.py        # WebSocket/HTTP 요청/응답 스키마
    │   ├── repositories/message_repo.py  # MongoDB CRUD + 커서 페이지네이션
    │   ├── services/chat_service.py      # 메시지 전송/조회/이벤트 로직
    │   ├── websocket/
    │   │   └── connection_manager.py     # WebSocket 연결 관리 (브로드캐스트)
    │   ├── routers/chat_router.py        # WebSocket + HTTP 엔드포인트
    │   ├── requirements.txt
    │   ├── Dockerfile
    │   └── main.py
    │
    └── notification-service/      # Kafka 기반 오프라인 알림 처리
        ├── core/
        │   ├── config.py          # 환경변수 (Redis, Kafka)
        │   └── redis_client.py    # Redis 비동기 클라이언트
        ├── consumers/
        │   └── message_consumer.py    # Kafka Consumer 이벤트 처리 루프
        ├── services/notify_service.py # 알림 CRUD (Redis 기반)
        ├── routers/notify_router.py   # 알림 조회/읽음 API
        ├── requirements.txt
        ├── Dockerfile
        └── main.py
```

---

## 서버 구동 방법

### 사전 요구사항

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치
- Git
- (선택) Python 3.11 — 로컬 단독 실행 시

### 1. 레포지토리 클론

```bash
git clone https://github.com/your-username/chat-platform.git
cd chat-platform
```

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다. (`.env.example` 참고)

```bash
cp .env.example .env
```

`.env` 파일 내용:

```env
# ── 공통 시크릿 ───────────────────────────────────────
SECRET_KEY=dev-secret-key-change-before-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── PostgreSQL ─────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://admin:password@postgres:5432/chatdb

# ── MongoDB ────────────────────────────────────────────
MONGO_URL=mongodb://mongo:27017
MONGO_DB=chatdb

# ── Redis ──────────────────────────────────────────────
REDIS_URL=redis://redis:6379

# ── Kafka ──────────────────────────────────────────────
KAFKA_URL=kafka:9092
KAFKA_GROUP_ID=notification-service
```

> **프로덕션 배포 시** `SECRET_KEY`를 반드시 강력한 랜덤 문자열로 변경하세요.

### 3. 전체 서비스 실행 (Docker Compose)

```bash
docker compose up --build
```

서비스 시작 순서는 Docker Compose가 자동으로 제어합니다:

```
Zookeeper → Kafka → Redis → user-service / chat-service / notification-service → Nginx
```

### 4. 실행 확인

| 서비스 | 헬스체크 URL | 포트 |
|---|---|---|
| Nginx Gateway | http://localhost/health | 80 |
| User Service | http://localhost/api/users/health | 8001 |
| Chat Service | http://localhost/api/chat/health | 8002 |
| Notification Service | http://localhost/api/notify/health | 8003 |

### 5. 개별 서비스 로컬 실행 (개발용)

```bash
# 인프라만 Docker로 실행
docker compose up redis kafka zookeeper

# user-service 단독 실행
cd services/user-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# chat-service 단독 실행
cd services/chat-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8002

# notification-service 단독 실행
cd services/notification-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8003
```

---

## API 명세

### User Service — `/api/users`

#### `POST /api/users/register` — 회원가입

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "홍길동",
  "password": "your-password"
}
```

**Response** `201 Created`:
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "홍길동",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00"
}
```

**에러 응답:**
- `400` — 이미 사용 중인 이메일 또는 유저명

---

#### `POST /api/users/login` — 로그인 (JWT 발급)

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response** `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**에러 응답:**
- `401` — 이메일 또는 비밀번호 불일치 / 비활성화된 계정

> 발급된 `access_token`은 이후 **WebSocket 연결** 및 **인증이 필요한 API**에서 사용됩니다.

---

#### `GET /api/users/{user_id}` — 유저 정보 조회

**Response** `200 OK`:
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "홍길동",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00"
}
```

**캐싱 전략:** Redis Cache-Aside 패턴 적용 (TTL 5분)

---

### Chat Service — `/api/chat`

#### `WS /api/chat/ws/{room_id}?token={JWT}` — WebSocket 채팅 연결

**연결 흐름:**
1. 쿼리 파라미터 `token`으로 JWT 검증
2. Redis에서 `user:{id}:username` 캐시 조회 (로그인 필수)
3. 연결 수락 → 입장 이벤트 브로드캐스트
4. 최근 메시지 자동 전송 (Redis 캐시 → MongoDB 폴백)

**클라이언트 → 서버 (메시지 송신):**
```json
{
  "content": "안녕하세요!"
}
```

**서버 → 클라이언트 (메시지 수신):**
```json
{
  "type": "message",
  "room_id": "general",
  "sender_id": 1,
  "sender_username": "홍길동",
  "content": "안녕하세요!",
  "created_at": "2025-01-01T12:00:00"
}
```

**서버 → 클라이언트 (입장/퇴장 이벤트):**
```json
{
  "type": "join",
  "room_id": "general",
  "sender_id": 1,
  "sender_username": "홍길동",
  "content": "홍길동님이 입장했습니다.",
  "created_at": "2025-01-01T12:00:00"
}
```

**서버 → 클라이언트 (입장 시 이전 메시지):**
```json
{
  "type": "history",
  "messages": [ ... ]
}
```

---

#### `GET /api/chat/rooms/{room_id}/messages` — 이전 메시지 조회

**Query Parameters:**

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `before` | datetime | null | 이 시각 이전의 메시지만 조회 (커서 페이지네이션) |
| `limit` | int | 50 | 조회할 메시지 수 (최대 100) |

**Response:**
```json
{
  "messages": [
    {
      "id": "65a1b2c3d4e5f6...",
      "room_id": "general",
      "sender_id": 1,
      "sender_username": "홍길동",
      "content": "안녕하세요!",
      "created_at": "2025-01-01T12:00:00"
    }
  ]
}
```

**페이지네이션 방법:**
```
# 첫 페이지
GET /api/chat/rooms/general/messages

# 다음 페이지 (마지막 메시지의 created_at 사용)
GET /api/chat/rooms/general/messages?before=2025-01-01T11:59:00&limit=50
```

---

#### `GET /api/chat/rooms/{room_id}/online` — 온라인 유저 목록

**Response:**
```json
{
  "room_id": "general",
  "online_users": [1, 3, 7]
}
```

---

### Notification Service — `/api/notify`

#### `GET /api/notify/{user_id}` — 알림 목록 + 읽지 않은 수 조회

**Response:**
```json
{
  "user_id": 1,
  "unread_count": 3,
  "notifications": [
    {
      "room_id": "general",
      "sender_username": "김철수",
      "content": "안녕하세요! 오늘 회의는...",
      "created_at": "2025-01-01T12:00:00",
      "is_read": false
    }
  ]
}
```

> 알림은 최근 50개까지 조회되며, 최대 100개 저장 (7일 TTL)

---

#### `POST /api/notify/{user_id}/read` — 전체 읽음 처리

**Response:**
```json
{
  "message": "모든 알림을 읽음 처리했습니다."
}
```

---

## 인프라 상세

### Nginx Gateway

| 설정 | 값 | 설명 |
|---|---|---|
| Rate Limit (일반 API) | 100 req/min, burst 20 | 일반 API 호출 제한 |
| Rate Limit (로그인) | 5 req/min, burst 3 | 무차별 대입 공격 방지 |
| WebSocket Timeout | 3600초 (1시간) | 장시간 WebSocket 연결 유지 |
| Worker Connections | 1024 | 동시 연결 처리 수 |
| Load Balancing | Upstream 블록 | 서비스 인스턴스 추가 시 라인 추가로 스케일 아웃 |

### PostgreSQL 커넥션 풀

| 설정 | 값 | 설명 |
|---|---|---|
| `pool_size` | 20 | 기본 유지 커넥션 수 |
| `max_overflow` | 40 | 풀 초과 시 추가 허용 |
| `pool_timeout` | 30초 | 커넥션 획득 대기 시간 |
| `pool_recycle` | 1800초 (30분) | 커넥션 재생성 주기 |
| **최대 동시 커넥션** | **60** | pool_size + max_overflow |

### Redis 활용 내역

| 키 패턴 | 서비스 | 용도 | TTL |
|---|---|---|---|
| `user:{id}` | user-service | 유저 프로필 캐시 | 5분 |
| `user:{id}:username` | user-service | username 캐시 (채팅용) | 1시간 |
| `user:{id}:status` | chat-service | 온라인 상태 | 5분 |
| `room:{id}:online` | chat-service | 채팅방 온라인 유저 SET | - |
| `room:{id}:recent` | chat-service | 최근 메시지 LIST (30개) | 1시간 |
| `room:{id}:members` | notification-service | 채팅방 멤버 SET | - |
| `notifications:{id}` | notification-service | 알림 LIST (100개) | 7일 |
| `unread:{id}` | notification-service | 읽지 않은 알림 카운터 | 7일 |

### Kafka 토픽

| 토픽 | Producer | Consumer | 설명 |
|---|---|---|---|
| `chat-messages` | chat-service | notification-service | 새 메시지 이벤트 |

- Consumer Group: `notification-service` — 스케일 아웃 시 파티션별 자동 분배로 중복 처리 방지
- Auto Offset Reset: `latest` — 서비스 재시작 시 새 메시지부터 처리

### MongoDB 인덱스

| 컬렉션 | 인덱스 | 용도 |
|---|---|---|
| `messages` | `room_id` | 채팅방별 메시지 조회 |
| `messages` | `created_at` | 시간순 정렬 |
| `messages` | `(room_id, created_at) DESC` | 복합 인덱스 — 페이지네이션 성능 최적화 |

---

## 주요 설계 포인트

### 대용량 트래픽 처리

- **비동기 전 구간**: FastAPI + asyncpg + Motor + aiokafka + aioredis — 모든 I/O가 비동기로 이벤트 루프 블로킹 없음
- **PostgreSQL 커넥션 풀**: 최대 60개 동시 커넥션으로 DB 병목 최소화
- **Redis 다층 캐싱**: 유저 프로필(5분), 최근 메시지(1시간), 온라인 상태(5분) — DB 부하 대폭 감소
- **커서 기반 페이지네이션**: OFFSET 방식 대비 대용량 데이터에서도 일정한 성능 유지

### MSA 설계

- **서비스 분리**: 유저 / 채팅 / 알림 — 독립 배포 및 스케일 아웃 가능
- **이벤트 기반 통신**: Kafka를 통한 서비스 간 비동기 메시지 전달 → 결합도 제거
- **기술 스택 혼용**: PostgreSQL(유저 정형 데이터) + MongoDB(메시지 비정형 데이터) — 데이터 특성에 맞는 DB 선택
- **헬스체크**: 각 서비스 `/health` 엔드포인트 제공

### 분산 환경 고려

- **Redis 온라인 상태 공유**: 서버 인스턴스가 여러 대일 때도 정확한 온라인 상태 판단
- **Kafka Consumer Group**: 스케일 아웃 시 중복 알림 방지
- **Redis Pipeline**: 다수 알림 읽음 처리 시 네트워크 왕복 최소화
- **Nginx Upstream**: 서비스 인스턴스 추가 시 설정 한 줄로 로드밸런싱

### 보안

- **bcrypt 비밀번호 해싱**: 평문 저장 없음
- **JWT 인증**: WebSocket 연결 시에도 토큰 검증 (쿼리 파라미터)
- **Rate Limiting**: 로그인 5req/min, 일반 API 100req/min
- **응답 보안**: UserResponse에 password 필드 미포함

---

## 개발 노트

- Python 3.11 기준, FastAPI 0.109 버전으로 작성되었습니다.
- 프로덕션 배포 시 `SECRET_KEY`는 반드시 환경변수로 교체하세요.
- Kafka 최초 실행 시 토픽 자동 생성까지 수 초 소요될 수 있습니다.
- `.env` 파일은 `.gitignore`에 반드시 포함하세요.
- Docker Compose는 healthcheck + depends_on 조건으로 서비스 시작 순서를 보장합니다.
- Kafka Producer/Consumer 모두 연결 실패 시 무한 재시도(5초 간격) 로직이 포함되어 있습니다.

---

## License

MIT
