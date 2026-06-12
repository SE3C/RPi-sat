# CubeSat Software Team

Raspberry Pi 5에서 실행 오류 점검을 하기 위한 큐브위성 소프트웨어팀 작업물입니다.

목표는 실제 센서 연결 테스트가 아니라, 각 담당 파일의 코드 구조와 import/runtime 오류를 점검할 수 있는 상태를 만드는 것입니다.

## 담당 파일

- 팀장: `main.py`, `config.py`, `requirements.txt`
- 팀원1: `sensors/gps.py`
- 팀원2: `sensors/dht11.py`, `sensors/bmp280.py`
- 팀원3: `sensors/mpu6050.py`, `sensors/bh1750.py`
- 팀원4: `output/led.py`, `output/buzzer.py`

## 실행

```bash
python3 main.py
```

센서나 GPIO 라이브러리가 설치되지 않았거나 하드웨어가 연결되지 않은 환경에서도 프로그램 전체가 바로 종료되지 않도록 작성했습니다.
