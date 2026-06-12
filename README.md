# CubeSat Software Team

Raspberry Pi 5에서 큐브위성 센서/출력 모듈의 import/runtime 오류를 함께 점검하기 위한 PR입니다.
목표는 실제 비행 코드 완성이 아니라, 각 담당 파일이 `main.py`에서 끊기지 않고 진단 결과를 반환하게 만드는 것입니다.

## 담당 파일

- 팀장: `main.py`, `config.py`, `requirements.txt`
- 팀원1: `sensors/gps.py`
- 팀원2: `sensors/dht11.py`, `sensors/bmp280.py`
- 팀원3: `sensors/mpu6050.py`, `sensors/bh1750.py`
- 팀원4: `output/led.py`, `output/buzzer.py`

## Raspberry Pi 설치/실행

```bash
cd ~/RPi-sat-pr
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

I2C 센서(BMP280, MPU6050, BH1750)를 실제로 읽으려면 Raspberry Pi 설정에서 I2C를 켜고 배선과 `config.py`의 주소/핀 값을 확인합니다.
GPS는 UART 포트, LED/버저는 GPIO 핀과 배선을 확인합니다.

## 반환 구조와 검증 기준

각 모듈은 실패해도 예외로 프로그램을 종료하지 않고 딕셔너리를 반환합니다.

- 정상 읽기: `status: "ok"` 또는 출력 모듈의 `ok: True`
- 실패/미연결: `status: "error"` 또는 `ok: False`, `error`, `debug`
- `debug`: 설정값, 사용하려 한 라이브러리, 의존성 상태, I2C/GPIO 핀, 실패 단계 같은 점검 정보

노트북이나 하드웨어 없는 환경에서 `No module named 'RPi'`, `No module named 'smbus2'`, 센서 미응답 같은 `error/debug`가 나오는 것은 정상입니다.
이 경우 검증 기준은 `python3 main.py`가 마지막까지 실행되고, 어떤 모듈이 왜 실패했는지 반환값에 표시되는지입니다.
