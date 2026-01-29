# 팰월드 세이브 양방향 변환기

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.7+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

팰월드 싱글 플레이 세이브와 서버 세이브를 양방향으로 변환하는 프로그램입니다.

버그 이슈로 그동안 비공개 했던 프로젝트입니다 이번 버그 수정으로 공개합니다

(아직 버그가 완전히 고쳐졌다고 확신은 못하는 상황입니다 그래도 여러부분이 고쳐졌습니다)

## 🎯 주요 기능

- ✅ **양방향 변환**: 싱글 ↔ 서버 세이브 변환
- ✅ **자동 정보 감지**: 월드 ID와 캐릭터 정보 자동 추출
- ✅ **안전한 백업**: 변환 전 자동 백업 생성
- ✅ **상세한 로깅**: 모든 작업 기록 및 오류 추적
- ✅ **도움말 시스템**: 메뉴바 도움말 및 입력 필드 툴팁
- ✅ **사용자 친화적 UI**: 직관적인 한국어 인터페이스

## 📋 시스템 요구사항

| 항목 | 요구사항 |
|------|---------|
| Python | 3.7 이상 |
| OS | Windows 7 이상 |
| RAM | 최소 512MB |
| 저장공간 | 최소 100MB |

## 🚀 빠른 시작

### 1단계: 라이브러리 설치

```bash
pip install palworld-save-tools
```

### 2단계: 프로그램 실행

```bash
python pal_migrator.py
```

## 📖 사용 방법

### 기본 사용 흐름

1. **파일 경로 설정**
   - 원본 Level.sav 파일 선택
   - 원본 Player.sav 파일 선택
   - 대상 Level.sav 파일 선택

2. **정보 자동 감지**
   - "파일 경로 기반 정보 자동 감지" 버튼 클릭
   - 월드 ID와 캐릭터 정보 확인

3. **변환 모드 선택**
   - **싱글 → 서버**: 싱글 플레이 세이브를 서버 세이브로 변환
   - **서버 → 싱글**: 서버 세이브를 싱글 플레이 세이브로 변환

4. **변환 시작**
   - "변환 시작" 버튼 클릭
   - 진행 상황 모니터링
   - 완료 메시지 확인

## 설치 가이드

### 방법 1: pip 사용 (권장)

```bash
pip install palworld-save-tools
python pal_migrator.py
```

### 방법 2: 특정 Python 버전 사용

Python 312를 사용하는 경우:

```bash
C:/Users/[사용자명]/AppData/Local/Programs/Python/Python312/python.exe -m pip install palworld-save-tools
C:/Users/[사용자명]/AppData/Local/Programs/Python/Python312/python.exe pal_migrator.py
```

### 방법 3: 강제 재설치

라이브러리 로드 오류가 발생하면:

```bash
pip uninstall -y palworld-save-tools
pip install --force-reinstall palworld-save-tools
python pal_migrator.py
```

## 🆘 문제 해결

### 문제 1: "No module named 'palworld_save_tools'"

**원인**: 라이브러리가 설치되지 않았거나 다른 Python 버전에 설치됨

**해결책**:
```bash
# 현재 Python 버전 확인
python --version

# 라이브러리 설치
python -m pip install palworld-save-tools

# 설치 확인
python -c "import palworld_save_tools; print('OK')"
```

### 문제 2: GUI가 나타나지 않음

**원인**: Tkinter가 설치되지 않았거나 권한 문제

**해결책**:
1. 관리자 권한으로 명령 프롬프트 열기
2. 다음 명령 실행:
```bash
python pal_migrator.py
```

### 문제 3: 라이브러리 로드 오류

**원인**: 라이브러리 버전 호환성 문제

**해결책**:
```bash
# 라이브러리 재설치
pip uninstall -y palworld-save-tools
pip install palworld-save-tools

# 프로그램 재실행
python pal_migrator.py
```

### 문제 4: 변환 실패

**원인**: 게임/서버가 실행 중이거나 파일 권한 문제

**해결책**:
1. 게임/서버 완전 종료
2. 관리자 권한으로 프로그램 실행
3. 로그 파일(migration.log) 확인

##  도움말 기능

### 메뉴바 도움말

프로그램 상단의 **"도움말"** 메뉴에서:

- **사용 가이드**: 단계별 사용 방법
- **FAQ**: 자주 묻는 질문 8개
- **정보**: 프로그램 정보 및 개발 정보

### 입력 필드 툴팁

각 입력 필드 위에 마우스를 올리면 해당 필드에 대한 설명이 나타납니다.

## 📝 주의사항

### 변환 전 체크리스트

- [ ] 게임/서버 완전 종료
- [ ] 충분한 저장 공간 확보 (최소 2배 이상)
- [ ] 파일 경로 정확성 확인
- [ ] 백업 경로 설정 (선택사항)

### 변환 중 주의사항

- 변환 중 프로그램 강제 종료 금지
- 변환 중 파일 수정 금지
- 변환 중 게임/서버 실행 금지

### 변환 후 확인사항

- [ ] 로그 파일에서 오류 확인
- [ ] 게임 시작 후 캐릭터 정상 작동 확인
- [ ] 필요시 백업 보관

## 🔄 백업 및 복구

### 백업 위치

기본적으로 월드 폴더의 다음 위치에 저장됩니다:
```
월드 폴더/Backup/SafeBackup_[타임스탬프]/
```

### 백업 복구 방법

변환 실패 시 백업에서 복구하는 방법:

1. 백업 폴더 열기
2. Level.sav 파일 복사
3. 원래 위치에 붙여넣기

## 📊 로그 파일

변환 후 문제가 발생하면 로그 파일을 확인하세요:

- **위치**: 설정한 로그 폴더 내 `migration.log`
- **내용**: 모든 변환 작업의 상세 기록

## 🎓 팰월드 세이브 파일 구조

- **Level.sav**: 월드 데이터 (플레이어 ID 포함)
- **Player.sav**: 캐릭터 데이터
- **LevelMeta.sav**: 월드 메타데이터
- **WorldOption.sav**: 월드 옵션

## 📄 파일 구조

```
pal_migrator.py          # 메인 프로그램
config.json              # 설정 파일 (자동 생성)
migration.log            # 로그 파일 (자동 생성)
```

## 안전성

- ✅ 변환 전 자동 백업
- ✅ 모든 작업 로깅
- ✅ 오류 발생 시 자동 중단
- ✅ 파일 무결성 검증

## 📝 변경 이력

### v1.0.0 (2025-10-24)
- 초기 릴리스
- 양방향 변환 기능
- 자동 정보 감지
- 안전한 백업 시스템
- 도움말 시스템
- 한국어 UI

## ⚠️ 면책 조항

이 프로그램은 팰월드 세이브 파일 변환을 위해 제공됩니다. 
사용자는 자신의 책임 하에 사용해야 하며, 데이터 손실에 대해 개발자는 책임을 지지 않습니다.
변환 전 반드시 백업을 생성하세요.

---

**버전**: 1.0.0  
**제작자**: Dangel
