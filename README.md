# 💬 실시간 채팅 플랫폼

MSA 기반 실시간 채팅 백엔드 시스템입니다.  
FastAPI + WebSocket + Kafka + Redis + Docker 를 활용한 대용량 트래픽 처리 구조를 구현합니다.

---

## 🏗️ 아키텍처

```
클라이언트
    │
    ▼
[Traefik Gateway :80]
    │
    ├─ /api/users/*    → user-service:8001
    ├─ /api/chat/*     → chat-service:8002
    └─ /api/notify/*   → notification-service:8003

         ↕                  ↕                    ↕
      [Redis]             [Kafka]              [Redis]
    세션/온라인상태       메시지 이벤트         알림 캐시

         ↕                  ↕
    [PostgreSQL]        [MongoDB]
      유저 정보           메시지 저장
```

---

## 📦 기술 스택

| 분류 | 기술 |
|---|---|
| 웹 프레임워크 | FastAPI |
| 실시간 통신 | WebSocket |
| 메시지 브로커 | Apache Kafka |
| 캐시 / 세션 | Redis |
| 유저 DB | PostgreSQL + SQLAlchemy (비동기) |
| 메시지 DB | MongoDB + Motor (비동기) |
| API 게이트웨이 | Traefik |
| 컨테이너 | Docker + Docker Compose |

---

## 🗂️ 프로젝트 구조

```
chat-platform/
├── docker-compose.yml
│
└── services/
    ├── user-service/              # 회원가입, 로그인, JWT 인증
    │   ├── core/
    │   │   ├── config.py          # 환경변수 설정
    │   │   ├── database.py        # PostgreSQL 커넥션 풀
    │   │   └── redis_client.py    # Redis 클라이언트
    │   ├── models/user.py         # DB 테이블 모델
    │   ├── schemas/user.py        # 요청/응답 스키마
    │   ├── repositories/          # DB CRUD
    │   ├── services/              # 비즈니스 로직 + 캐싱
    │   ├── routers/               # API 엔드포인트
    │   └── main.py
    │
    ├── chat-service/              # WebSocket, 실시간 메시지 처리
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── mongo_client.py    # MongoDB 클라이언트
    │   │   ├── redis_client.py
    │   │   └── kafka_client.py    # Kafka Producer
    │   ├── models/message.py      # 메시지 문서 모델
    │   ├── schemas/chat.py
    │   ├── repositories/          # MongoDB CRUD
    │   ├── services/              # 메시지 송수신, 캐싱
    │   ├── websocket/
    │   │   └── connection_manager.py  # WebSocket 연결 관리
    │   ├── routers/
    │   └── main.py
    │
    └── notification-service/      # Kafka Consumer, 알림 처리
        ├── core/
        │   ├── config.py
        │   └── redis_client.py
        ├── consumers/
        │   └── message_consumer.py    # Kafka 메시지 소비
        ├── services/                  # 알림 저장/조회
        ├── routers/
        └── main.py
```

---

## 🚀 시작하는 법

### 사전 요구사항

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치
- Git

### 1. 레포지토리 클론

```bash
git clone https://github.com/your-username/chat-platform.git
cd chat-platform
```

### 2. 환경변수 설정

각 서비스 디렉토리에 `.env` 파일 생성 (`.env.example` 참고)

```bash
# services/user-service/.env
DATABASE_URL=postgresql+asyncpg://admin:password@postgres:5432/chatdb
REDIS_URL=redis://redis:6379
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

```bash
# services/chat-service/.env
MONGO_URL=mongodb://mongo:27017
MONGO_DB=chatdb
REDIS_URL=redis://redis:6379
KAFKA_URL=kafka:9092
SECRET_KEY=your-secret-key-change-in-production
```

```bash
# services/notification-service/.env
REDIS_URL=redis://redis:6379
KAFKA_URL=kafka:9092
KAFKA_GROUP_ID=notification-service
```

### 3. 전체 서비스 실행

```bash
docker compose up --build
```

### 4. 실행 확인

| 서비스 | 주소 |
|---|---|
| Traefik 대시보드 | http://localhost:8080 |
| User Service | http://localhost/api/users/health |
| Chat Service | http://localhost/api/chat/health |
| Notification Service | http://localhost/api/notify/health |

---

## 📡 API 명세

### User Service `/api/users`

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/register` | 회원가입 |
| POST | `/login` | 로그인 (JWT 발급) |
| GET | `/{user_id}` | 유저 조회 (Redis 캐시) |

### Chat Service `/api/chat`

| Method | Endpoint | 설명 |
|---|---|---|
| WS | `/ws/{room_id}?user_id=1&username=홍길동` | WebSocket 연결 |
| GET | `/rooms/{room_id}/messages` | 이전 메시지 조회 (커서 페이지네이션) |
| GET | `/rooms/{room_id}/online` | 온라인 유저 목록 |

### Notification Service `/api/notify`

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/{user_id}` | 알림 목록 + 읽지 않은 수 조회 |
| POST | `/{user_id}/read` | 전체 읽음 처리 |

---

## 🔄 실시간 메시지 흐름

```
유저A → WebSocket 전송
    │
    ▼
chat-service
    ├─ MongoDB 저장          (영구 보관)
    ├─ broadcast()           (온라인 유저 즉시 수신)
    ├─ Kafka publish         (이벤트 발행)
    └─ Redis 캐시            (최근 30개 메시지)
              │
              ▼
    notification-service
    (Kafka Consumer)
              │
              ├─ 온라인 유저  → skip (이미 받음)
              └─ 오프라인 유저 → Redis 알림 저장
                                    │
                                    ▼
                            다음 접속 시 알림 수신
```

---

## ⚙️ 주요 설계 포인트

### 대용량 트래픽 처리

- **PostgreSQL 커넥션 풀** : `pool_size=20`, `max_overflow=40` 으로 최대 60개 동시 커넥션 처리
- **Redis 캐시** : 유저 프로필 (TTL 5분), 최근 메시지 (TTL 1시간) 캐싱으로 DB 부하 감소
- **비동기 처리** : FastAPI + asyncpg + motor 전 구간 비동기 I/O

### MSA 설계

- **서비스 분리** : 유저 / 채팅 / 알림 독립 배포 및 스케일 아웃 가능
- **이벤트 기반 통신** : Kafka를 통한 서비스 간 비동기 메시지 전달로 결합도 제거
- **헬스체크** : 각 서비스 `/health` 엔드포인트 → Traefik 자동 장애 감지

### 분산 환경 고려

- **Redis 온라인 상태 공유** : 서버 인스턴스 여러 대일 때도 정확한 온라인 상태 판단
- **Kafka Consumer Group** : 스케일 아웃 시 중복 알림 방지
- **Redis Pipeline** : 다수 알림 읽음 처리 시 네트워크 왕복 최소화

### 데이터 설계

- **PostgreSQL** : 유저 정보 (정형 데이터, 관계 중요)
- **MongoDB** : 메시지 저장 (비정형, 대용량, 스키마 변경 잦음)
- **커서 기반 페이지네이션** : 대용량 메시지 조회 시 OFFSET 방식 대비 성능 우위

---

## 🛠️ 개발 환경 (단일 서비스 실행)

```bash
# 인프라만 실행
docker compose up postgres redis mongo kafka zookeeper

# user-service만 단독 실행 (로컬 개발 시)
cd services/user-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

---

## 📊 부하 테스트

[Locust](https://locust.io/) 를 활용한 부하 테스트로 성능 지표를 측정합니다.

```bash
pip install locust
locust -f locustfile.py --host=http://localhost
```

테스트 시나리오:
- 동시 접속자 수별 응답시간 측정
- Redis 캐시 적용 전/후 성능 비교
- WebSocket 동시 연결 처리량 측정

---

## 🗒️ 개발 노트

- Python 3.11 기준으로 작성되었습니다.
- 프로덕션 배포 시 `SECRET_KEY` 는 반드시 환경변수로 교체하세요.
- Kafka 최초 실행 시 토픽 자동 생성까지 수 초 소요될 수 있습니다.
- `.env` 파일은 `.gitignore` 에 반드시 포함하세요.

---

## 📝 License

MIT
