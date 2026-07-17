[English](../../README.md) / [简体中文](README.zh-CN.md) / [日本語](README.ja.md) / [한국어](README.ko.md)

# PitchMind — Football AI Analysis Engine

![PitchMind 브랜드 커버](../assets/pitchmind-hero.png)

**PitchMind는 축구 경기 리서치를 local-first 데스크톱 워크플로로 정리합니다. 경기 맥락 수집, AI 지원 분석, 근거 검토, 보고서 내보내기를 개인 token이나 로컬 run 데이터를 호스팅 제품으로 보내지 않고 진행할 수 있습니다.**

[공개 Beta 4 다운로드](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4) · [제품 둘러보기](#제품-둘러보기) · [개발자 문서](../DEVELOPMENT.md)

> 준수 경계: PitchMind는 연구, 학습, 엔터테인먼트를 위한 도구입니다. 베팅 조언, 금융 조언 또는 경기 결과 보장이 아닙니다.

## 사용 가능한 데스크톱 Beta

**최신 공개 프리릴리스:** [`desktop-beta-4`](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)

**최신 자동 CI Draft:** `desktop-beta-8`은 Draft 릴리스 자동화 경로를 증명하기 위한 것이며, 일반 사용자의 일반 다운로드 입구가 아닙니다.

| 플랫폼 | 상태 | 공개 Beta 4 에셋 |
| --- | --- | --- |
| Windows x64 | 사용 가능 | `PitchMind-Setup-x64.exe` |
| macOS Apple Silicon | 사용 가능 | `PitchMind-macOS-AppleSilicon.dmg` |
| macOS Intel | 사용 가능 | `PitchMind-macOS-Intel.dmg` |

이 Beta는 서명되지 않았습니다. 설치 중 운영체제의 보안 경고가 표시될 수 있습니다. 위 공식 GitHub Release에서만 다운로드하고, 제공되는 경우 에셋 이름과 체크섬을 확인하세요. 미러나 재업로드된 파일은 설치하지 마세요.

## 제품 둘러보기

![PitchMind 제품 둘러보기](../assets/pitchmind-product-tour.png)
## 3단계로 시작하기

1. [`desktop-beta-4` 릴리스 페이지](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)를 열고 사용 중인 플랫폼에 맞는 설치 파일을 다운로드합니다.
2. PitchMind를 설치하고 실행합니다. 서명되지 않은 Beta이므로, 파일이 공식 릴리스 페이지에서 온 것이 확실할 때만 운영체제 보안 경고를 승인하세요.
3. 로컬 run을 만들고 데이터 품질 메모와 보고서를 확인합니다. 연구 결과를 공유해야 한다면 사용 가능한 artifact를 내보내세요.

## 핵심 기능

| 영역 | PitchMind가 도와주는 일 |
| --- | --- |
| 경기 리서치 | 축구 경기 번호, 데이터 소스 상태, 분석 run을 하나의 로컬 작업 공간에서 정리합니다. |
| AI 지원 보고서 | 근거 메모, 사용 가능한 prediction JSON, 준수 알림이 포함된 구조화된 축구 분석 보고서를 생성합니다. |
| Run 기록과 내보내기 | 이전 run, 상태, 보고서 artifact, 내보낼 수 있는 결과를 검토합니다. |
| local-first 개인정보 보호 | 설정, token, 로컬 데이터베이스, 생성된 run 파일을 사용자의 컴퓨터에 보관합니다. |
| 안전 경계 | 제품 흐름 안에서 서명되지 않은 Beta 상태와 연구용 사용 범위를 명확히 보여줍니다. |

## 검증된 과거 성과

아래 수치는 102개의 raw ledger 항목에서 86개의 clean 경기 전 샘플을 추려 재구성한 평가값입니다. 1X2 정확도는 clean 세트를 사용합니다. 정확한 스코어 Top 3 포함률은 과거 `lh`/`la` 값을 현재 `score_matrix` 채점 방식으로 다시 계산한 것입니다. 이는 모델 평가 증거이며 미래 경기 결과를 보장하지 않습니다.

![PitchMind 검증된 과거 성과 데이터 대시보드](../assets/pitchmind-performance.svg)

| 평가 세트 | 결과 |
| --- | ---: |
| Raw ledger 항목 | 102경기 |
| Clean 경기 전 샘플 | 86경기 |
| 1X2 방향 정확도 | **64/86 (74.4%)** |
| 정확한 스코어 Top 3 포함률 | **33/86 (38.4%)** |

경기 시작 전에 저장된 정확한 스코어 적중 사례:

| 경기 | 경기 전 모델 스코어 | 최종 스코어 | 적중 |
| --- | --- | ---: | --- |
| 아르헨티나 vs 오스트리아 | **2-0** / 1-0 / 3-0 | **2-0** | Top 1 |
| 프랑스 vs 이라크 | **3-0** / 2-0 / 4-0 | **3-0** | Top 1 |
| 브라질 vs 아이티 | **3-0** / 4-0 / 5-0 | **3-0** | Top 1 |
| 프랑스 vs 스웨덴 | **3-0** / 4-0 / 2-0 | **3-0** | Top 1 |
| 미국 vs 보스니아 헤르체고비나 | **2-0** / 3-0 / 2-1 | **2-0** | Top 1 |
| 포르투갈 vs 크로아티아 | **2-1** / 1-1 / 3-1 | **2-1** | Top 1 |
| 스페인 vs 오스트리아 | 2-0 / **3-0** / 1-0 | **3-0** | Top 3 |
| 스위스 vs 알제리 | 1-1 / 2-1 / **2-0** | **2-0** | Top 3 |

위 표는 선별한 성공 사례입니다. 엔진 평가는 적중과 실패를 모두 포함한 전체 집계 수치를 기준으로 해야 합니다.

## 릴리스 품질 증거

| 증거 | 상태 |
| --- | --- |
| 자동화 테스트 | 릴리스 품질 게이트에서 146개 테스트 통과. |
| 네이티브 데스크톱 CI | Windows x64, macOS Apple Silicon, macOS Intel 세 릴리스 작업이 플랫폼별 설치 파일을 생성합니다. |
| 릴리스 에셋 | 공개 Beta 4는 설치 파일을 제공하며, 릴리스 페이지에 `SHA256SUMS.txt` 같은 체크섬/릴리스 자료가 첨부됩니다. |
| local-first 경계 | 현재 서명되지 않은 Beta 단계에서는 클라우드 동기화, 원격 텔레메트리, 자동 서명 업데이트를 주장하지 않습니다. |

## 개인정보 보호와 서명되지 않은 Beta 안전

- PitchMind는 사용자의 컴퓨터에서 로컬로 실행되도록 설계되었습니다.
- 지원을 요청할 때 API token, 계정 token, `.env` 파일, 로컬 데이터베이스 또는 run artifact를 보내지 마세요.
- 브라우저 또는 데스크톱의 token 입력은 사용자의 로컬 워크플로를 위한 것입니다. token은 비밀 정보로 취급하세요.
- 현재 데스크톱 Beta는 코드 서명되지 않았으며 자동 업데이트를 지원한다고 주장하지 않습니다. 서명되지 않은 프리뷰 소프트웨어가 불편하다면 서명된 릴리스를 기다려 주세요.

## 피드백

버그, 설치 문제, 사용성 피드백은 [GitHub Issues](https://github.com/0801ljw/football-ai-analysis-engine/issues)에 남겨 주세요. 운영체제, 다운로드한 에셋 이름, 발생한 일을 함께 적어 주세요. token이나 로컬 개인 데이터는 포함하지 마세요.

## 기술과 개발자 입구

| 계층 | 스택 |
| --- | --- |
| 데스크톱 셸 | Tauri |
| 로컬 웹 앱 | FastAPI, Jinja2 |
| 프런트엔드 자산 | HTML, CSS, JavaScript |
| 런타임과 도구 | Python, SQLite, PyInstaller sidecar, 릴리스 패키징 스크립트 |
| 릴리스 대상 | GitHub Releases, 수동 서명되지 않은 Beta 배포 |

개발자 입구:

- [개발자 문서](../DEVELOPMENT.md)
- [데스크톱 Beta 설치 노트](../../desktop/INSTALL_BETA.md)
- [릴리스 체크리스트](../../RELEASE_CHECKLIST.md)
- [데스크톱 소스 README](../../desktop/README.md)

## 법률 및 준수 알림

PitchMind는 축구 데이터 연구, 확률적 탐색, 콘텐츠 제작 보조를 엔터테인먼트와 학습 목적으로 제공합니다. 베팅 조언, 보장된 예측 또는 베팅 지시는 제공하지 않습니다. 항상 거주 지역의 법률과 사용하는 플랫폼의 규칙을 따르세요.
