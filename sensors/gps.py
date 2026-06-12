 # sensors/gps.py
import serial
import pynmea2
import config  # config.py의 GPS_PORT, GPS_BAUDRATE 참조

# [오류 방지 1] 전역 변수를 이용해 시리얼 객체를 유지 (매번 Open/Close 방지)
_ser_instance = None

# [오류 방지 2] 최신 수신 성공 데이터를 유지하는 전역 버퍼 (RMC, GGA 데이터 통합 유지)
_gps_state = {
    "latitude": None,
    "longitude": None,
    "altitude": None,
    "num_satellites": 0,
    "error_message": None
}

# [오류 방지 3] 내일 장비 미연결/실내 테스트용 고정 임시 데이터 (Mock Data)
MOCK_DATA = {
    "latitude": 37.5665,      # 서울 위도
    "longitude": 126.9780,    # 서울 경도
    "altitude": 45.2,         # 임시 고도
    "num_satellites": 5,      # 가상 위성 수
    "error_message": "No Hardware Stream. Returning Mock Data."
}

def read_gps_data():
    """
    main.py에서 무한 루프로 호출하더라도 안전하게 GPS 상태를 반환하는 함수입니다.
    기존 코드의 포트 반복 개방 문제, 데이터 증발 문제, 임시값 누락 문제를 모두 해결했습니다.
    """
    global _ser_instance, _gps_state
    
    # 1. 기본 반환 템플릿 생성 (기존에 수신된 최신 상태 복사)
    output = _gps_state.copy()
    output["error_message"] = None  # 매 호출마다 에러 메시지는 새로 갱신

    try:
        # config.py에서 설정값 안전하게 가져오기 (없으면 기본값 사용)
        port = getattr(config, 'GPS_PORT', '/dev/serial0')
        baudrate = getattr(config, 'GPS_BAUDRATE', 9600)
        
        # [해결 1] 시리얼 포트가 없거나 닫혀있을 때만 최초 1회/재연결 시도
        if _ser_instance is None or not _ser_instance.is_open:
            _ser_instance = serial.Serial(port, baudrate=baudrate, timeout=0.1)
            
        # 2. 시리얼 버퍼에 읽을 데이터가 있는지 확인
        if _ser_instance.in_waiting > 0:
            # raw NMEA 한 줄 읽기
            raw_line = _ser_instance.readline().decode('utf-8', errors='ignore').strip()
            
            if raw_line.startswith('$GPRMC') or raw_line.startswith('$GPGGA'):
                msg = pynmea2.parse(raw_line)
                
                # [해결 2] 각 문장에서 나오는 데이터만 부분 업데이트하여 전역 버퍼에 누적
                if raw_line.startswith('$GPRMC'):
                    if msg.status == 'A':  # 신호 정상 수신 시 위도/경도 업데이트
                        _gps_state["latitude"] = msg.latitude
                        _gps_state["longitude"] = msg.longitude
                    else:
                        # 실내 미연결 시 실패 처리 안 함, 로그만 남김
                        output["error_message"] = "GPS Signal Void (Indoor/Searching)"
                        
                elif raw_line.startswith('$GPGGA'):
                    if msg.gps_qual > 0:  # Fix 품질 유효 시 위도/경도/고도 업데이트
                        _gps_state["latitude"] = msg.latitude
                        _gps_state["longitude"] = msg.longitude
                        _gps_state["altitude"] = msg.altitude
                    # 위성 수는 Fix 여부와 관계없이 실시간 반영
                    _gps_state["num_satellites"] = int(msg.num_sats) if msg.num_sats else 0
                
                # 전역 버퍼의 최신 누적 데이터를 반환값에 반영
                output.update({
                    "latitude": _gps_state["latitude"],
                    "longitude": _gps_state["longitude"],
                    "altitude": _gps_state["altitude"],
                    "num_satellites": _gps_state["num_satellites"]
                })
        else:
            # [해결 3] 장치가 연결 안 되었거나 데이터 스트림이 없는 상태 대응
            # 아직 실데이터 수신 이력이 없다면 즉시 안전하게 Mock 데이터 공급
            if _gps_state["latitude"] is None:
                output.update(MOCK_DATA)
                output["error_message"] = "Waiting for hardware stream... [Mocking Active]"

    except serial.SerialException as se:
        # 포트 에러, 미연결, 케이블 분리 등 하드웨어 오류 발생 시
        _ser_instance = None  # 에러 발생 시 포트 객체를 비워 다음 루프 때 재연결 유도
        
        # 실데이터 수신 이력이 없을 때만 Mock 데이터로 덮어쓰기 하여 main.py 무중단 보장
        if _gps_state["latitude"] is None:
            output.update(MOCK_DATA)
        output["error_message"] = f"Serial Connection Error: {str(se)}"
        
    except pynmea2.ParseError as pe:
        # NMEA 데이터 유실/깨짐 시 전체 프로그램에 영향 없도록 방어
        output["error_message"] = f"NMEA Parsing Error: {str(pe)}"
        
    except Exception as e:
        # 기타 모든 예측 불허 예외 방어
        output["error_message"] = f"Unexpected GPS Error: {str(e)}"
        
    return output
