# statutes는 아직 실 데이터가 없어 파이프라인 검증용 가상(fictional) 샘플을 그대로 쓴다.
# precedents/interpretations/adjudications는 실 데이터로 교체 완료(rag_sources.py의 REAL_DATA_FILES 참고).

MOCK_DOCUMENTS: dict[str, list[str]] = {
    "statutes": [
        "[가상 샘플] 민법 제618조: 임대차는 당사자 일방이 상대방에게 목적물을 사용, 수익하게 할 것을 약정하고 상대방이 이에 대하여 차임을 지급할 것을 약정함으로써 효력이 생긴다.",
        "[가상 샘플] 민법 제750조: 고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.",
        "[가상 샘플] 민법 제162조: 채권은 10년간 행사하지 아니하면 소멸시효가 완성한다.",
    ],
}
