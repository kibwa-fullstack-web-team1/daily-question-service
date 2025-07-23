from confluent_kafka import Producer
import json
from app.config.config import Config # Config 임포트

# Kafka 브로커 URL을 Config에서 가져옵니다.
KAFKA_BROKER_URL = Config.KAFKA_BROKER_URL

def delivery_report(err, msg):
    """
    Kafka 메시지 전송 결과를 로깅합니다.
    """
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to topic '{msg.topic()}' [{msg.partition()}] at offset {msg.offset()}")

def publish_score_update(user_id: str, answer_id: str, cognitive_score: float, semantic_score: float, timestamp: str):
    """
    인지 건강 점수 및 맥락 점수 업데이트 메시지를 Kafka에 발행합니다.
    """
    producer = Producer({'bootstrap.servers': KAFKA_BROKER_URL})

    message_payload = {
        "user_id": user_id,
        "answer_id": answer_id,
        "cognitive_score": cognitive_score,
        "semantic_score": semantic_score,
        "timestamp": timestamp
    }
    # 메시지 페이로드를 JSON 문자열로 변환
    message_json = json.dumps(message_payload)

    # 'score-updates' 토픽으로 메시지 발행
    producer.produce(
        'score-updates',
        key=str(user_id), # user_id를 키로 사용하여 같은 유저의 메시지가 같은 파티션으로 가도록 함
        value=message_json.encode('utf-8'),
        callback=delivery_report
    )
    # 버퍼에 있는 모든 메시지가 전송되도록 강제합니다.
    producer.flush()
