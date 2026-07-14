[English](../../README.md) / [简体中文](README.zh-CN.md) / [日本語](README.ja.md) / [한국어](README.ko.md)

# PitchMind — Football AI Analysis Engine

![PitchMind 브랜드 커버](../assets/pitchmind-hero.png)

**PitchMind**는 축구 경기 리서치, AI 지원 분석, 구조화된 보고서 생성을 위한 local-first(로컬 우선) 데스크톱 Beta입니다. 일반 사용자가 집중해서 사용할 수 있는 연구 작업 공간을 제공하며, 개인 token이나 로컬 run 데이터를 호스팅 서비스로 보내는 것을 전제로 하지 않습니다.

> 준수 경계: PitchMind는 연구와 엔터테인먼트를 위한 도구입니다. 베팅 조언, 금융 조언 또는 경기 결과 보장이 아닙니다.

## 데스크톱 Beta 다운로드

**최신 Beta:** [`desktop-beta-4`](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)

| 플랫폼 | 상태 | 에셋 |
| --- | --- | --- |
| Windows x64 | 사용 가능 | `PitchMind-Setup-x64.exe` |
| macOS Apple Silicon | 사용 가능 | `PitchMind-macOS-AppleSilicon.dmg` |
| macOS Intel | 아직 사용 불가 | 이번 릴리스에는 Intel DMG가 없습니다 |

이 Beta는 서명되지 않았습니다. 설치 중 운영체제의 보안 경고가 표시될 수 있습니다. 위 공식 GitHub Release에서만 다운로드하고, 미러나 재업로드된 파일은 설치하지 마세요.

## 무엇을 할 수 있나요

| 영역 | PitchMind가 도와주는 일 |
| --- | --- |
| 경기 리서치 | 축구 경기 번호, 데이터 소스 상태, 분석 run을 하나의 로컬 작업 공간에서 정리합니다. |
| AI 지원 보고서 | 데이터 품질 메모와 준수 알림이 포함된 구조화된 축구 분석 보고서를 생성합니다. |
| Run 기록 | 이전 run, 상태, 내보낸 artifact, 사용 가능한 prediction JSON을 검토합니다. |
| 로컬 우선 워크플로 | 설정, token, 생성된 run 파일을 사용자의 컴퓨터에 보관합니다. |
| 안전 경계 | 서명되지 않은 Beta 안내를 명확히 보여주고, 출력이 연구와 엔터테인먼트 용도임을 알립니다. |

## 3단계 빠른 시작

1. [`desktop-beta-4` 릴리스 페이지](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)를 열고 사용 중인 플랫폼에 맞는 설치 파일을 다운로드합니다.
2. PitchMind를 설치하고 실행합니다. 서명되지 않은 Beta이므로, 파일이 공식 릴리스 페이지에서 온 것이 확실할 때만 운영체제 보안 경고를 승인하세요.
3. 로컬 run을 만들고 데이터 품질 메모를 확인합니다. 연구 결과를 공유해야 한다면 사용 가능한 artifact를 내보내세요.

## 개인정보 보호와 local-first 사용

- PitchMind는 사용자의 컴퓨터에서 로컬로 실행되도록 설계되었습니다.
- 지원을 요청할 때 API token, 계정 token, `.env` 파일, 로컬 데이터베이스 또는 run artifact를 보내지 마세요.
- 브라우저 또는 데스크톱의 token 입력은 사용자의 로컬 워크플로를 위한 것입니다. token은 비밀 정보로 취급하세요.
- 이 README는 원격 텔레메트리, 클라우드 동기화 또는 자동 업데이트 동작을 주장하지 않습니다.

## 서명되지 않은 Beta 안전 안내

현재 데스크톱 Beta는 코드 서명되지 않았으며 자동 업데이트를 지원한다고 주장하지 않습니다. Windows 또는 macOS가 서명되지 않은 프리뷰 소프트웨어에 보안 경고를 표시하는 것은 예상되는 동작입니다. 불편하다면 서명된 릴리스를 기다려 주세요.

## 피드백과 Issue

버그, 설치 문제, 사용성 피드백은 [GitHub Issues](https://github.com/0801ljw/football-ai-analysis-engine/issues)에 남겨 주세요. 운영체제, 다운로드한 에셋 이름, 발생한 일을 함께 적어 주세요. token이나 로컬 개인 데이터는 포함하지 마세요.

## 기술 스택

| 계층 | 스택 |
| --- | --- |
| 데스크톱 셸 | Tauri |
| 로컬 웹 앱 | FastAPI, Jinja2 |
| 프런트엔드 자산 | HTML, CSS, JavaScript |
| 런타임과 도구 | Python, SQLite, PyInstaller sidecar, 릴리스 패키징 스크립트 |
| 릴리스 대상 | GitHub Releases, 수동 서명되지 않은 Beta 배포 |

## 개발자 입구

이 랜딩 페이지는 일반 사용자를 위한 것입니다. 기존 개발자 README는 다시 쓰지 않고 그대로 보존했습니다.

- [개발자 문서](../DEVELOPMENT.md)
- [데스크톱 Beta 설치 노트](../../desktop/INSTALL_BETA.md)
- [릴리스 체크리스트](../../RELEASE_CHECKLIST.md)
- [데스크톱 소스 README](../../desktop/README.md)

## 법률 및 준수 알림

PitchMind는 축구 데이터 연구, 확률적 탐색, 콘텐츠 제작 보조를 엔터테인먼트와 학습 목적으로 제공합니다. 베팅 조언, 보장된 예측 또는 베팅 지시는 제공하지 않습니다. 항상 거주 지역의 법률과 사용하는 플랫폼의 규칙을 따르세요.
