from switchcraft.services.exchange_service import ExchangeService

def test_mail_flow_service():
    service = ExchangeService()

    # 1. Test Stats Mock
    stats = service.get_mail_traffic_stats(token="mock")
    print(f"Stats Length: {len(stats)}")
    assert len(stats) == 7
    print(f"Sample Stat: {stats[0]}")
    assert "sent" in stats[0]

    # 2. Test Send Mail (Mock - validation logic inside service requires real token,
    # but we can check if it initializes)
    print("Exchange Service initialized successfully.")

if __name__ == "__main__":
    test_mail_flow_service()
