# 소프트웨어팀 작업 안내

소프트웨어팀 팀원은 태블릿으로 GitHub에서 자기 담당 파일만 수정합니다.

`main.py`, `config.py`, `requirements.txt`는 수정 금지입니다.

다른 사람의 담당 파일은 수정 금지입니다.

공통 구조 변경이 필요하면 리더에게 먼저 요청합니다.

## 이번 PR 목적

각 담당 모듈이 Raspberry Pi에서 실행될 때 import 오류, 라이브러리 누락, 하드웨어 미연결 오류를 프로그램 종료 대신 반환값으로 보여주게 합니다.
실제 센서값이 없더라도 어느 단계에서 실패했는지 팀원이 확인할 수 있어야 합니다.

## 반환값 규칙

- 센서 모듈은 `status`, 측정값, `error`, `debug`를 반환합니다.
- LED/버저 모듈은 `ok`, `device`, `action`, `errors`, `debug`를 반환합니다.
- `debug`에는 설정값, 라이브러리 설치 상태, 사용한 핀/주소, 실패 단계 같은 점검 정보를 넣습니다.

하드웨어가 없는 PC나 태블릿 테스트 환경에서는 `status: "error"`, `ok: False`, `debug`가 나오는 것이 정상입니다.
중요한 것은 예외로 멈추지 않고 `main.py`가 끝까지 실행되는 것입니다.

## Raspberry Pi에서 확인

```bash
cd ~/RPi-sat-pr
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

실행 결과에서 자기 담당 모듈 줄을 확인합니다.
실패했다면 `error`와 `debug`를 보고 라이브러리 설치 문제인지, 설정값 문제인지, 배선/센서 응답 문제인지 구분합니다.

## 담당 파일

- 팀원1: `sensors/gps.py`
- 팀원2: `sensors/dht11.py`, `sensors/bmp280.py`
- 팀원3: `sensors/mpu6050.py`, `sensors/bh1750.py`
- 팀원4: `output/led.py`, `output/buzzer.py`
