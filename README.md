# Oracle MVP AI

사내 프롬프트 평가 및 AI 판정 자동화를 위한 Python 라이브러리 및 Playground

---

## 프로젝트 구조

```
root
│
├── lib/                  # 라이브러리(비즈니스 로직, 모델, 유틸)
│   ├── ai_judge.py       # AI 판정 메인 클래스
│   ├── openai_client.py  # OpenAI API 통신 모듈
│   ├── core.py           # export 빌드 파일
│   └── __init__.py       # 패키지 초기화
│
├── metrics/              # 평가지표, 실험, 테스트 코드
│   └── a.test.py
│
├── prompt_metadata/      # 프롬프트 메타데이터(yaml, 수정/삭제 불가)
│   ├── v_1_0_1.yaml
│   ├── v_1_0_2.yaml
│   └── README.md
│
├── playground/           # API 및 UI 테스트 환경
│   ├── api.py            # FastAPI 서버 (질문/응답 API)
│   └── ui/               # nicegui 기반 웹 UI
│       └── main.py
│
└── README.md             # 메인 설명서
```

---

## 주요 기능

- **AI Judge 라이브러리**: 프롬프트(yaml)와 의견 리스트, 주제를 받아 OpenAI API로 판정 결과 반환
- **프롬프트 버전 관리**: prompt_metadata 폴더 내 yaml 파일로 프롬프트 버전별 관리 (수정/삭제 불가, 추가만 가능)
- **Playground**: FastAPI 및 nicegui 기반 웹 UI로 실제 프롬프트/의견/주제 입력 및 결과 확인
- **평가지표(metrics)**: 답변 평가용 함수 예시 제공 (루트 metrics 폴더 참고)

---

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (.env 파일 사용)

```
OPENAI_API_KEY=
```

### 3. FastAPI 서버 실행

```bash
uvicorn playground.api:app --reload
```

### 4. nicegui UI 실행

```bash
python playground/ui/main.py
```

---

## 개발/배포 가이드

- **라이브러리 배포**: `lib/` 내 코드는 사내 PyPI 서버에 업로드 가능 (core.py에서 export)
- **프롬프트 관리**: prompt_metadata 폴더 내 yaml 파일은 수정/삭제 불가, 버전 추가만 허용
- **테스트/확장**: playground에서 API 및 UI로 기능 테스트, metrics 폴더에서 평가지표 함수 추가 가능

# oracle-mvp-ai

AI 판정 시스템 (AiJudge)

## 설치 방법

사내 PyPI 서버에서 설치:

```
pip install --index-url http://{ip}:{port}/simple/ oracle-mvp-ai
```

## 주요 클래스

- `AiJudge`: AI 기반 판정 시스템의 메인 클래스

## 예제 코드

```python
from lib import AiJudge, OpenAIClient

openai_client = OpenAIClient(api_key="YOUR_OPENAI_API_KEY")
judge = AiJudge(openai_client)

# 예시 데이터
sample_data = {
    "topic": {
        "title": "VAR 도입이 축구에 긍정적인가?",
        "description": "비디오 판독(VAR) 도입의 장단점에 대한 토론.",
        "camps": [
            {"id": 1, "name": "찬성"},
            {"id": 2, "name": "반대"}
        ]
    },
    "posts": [
        {"user_id": 1, "msg": "VAR은 오심을 줄여줍니다."},
        {"user_id": 2, "msg": "경기 흐름이 자주 끊깁니다."}
    ]
}

result = judge.judge(sample_data)
print(result)
```

## 배포 방법

1. 패키지 빌드
   ```
   python setup.py sdist bdist_wheel
   ```
2. 사내 PyPI 서버 업로드
   ```
   twine upload --repository pypi dist/*
   ```
   (pypirc 파일에 사내 서버 정보 필요)

## 기타

- `prompt_metadata/` 폴더 내 프롬프트 yaml 파일 필요
- `openai`, `pyyaml` 패키지 필요
