import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Receipt, Vendor
from services.journal_generator import JournalGenerator
from schemas import PaymentMethod

# テスト用データベース
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_tax_calculation():
    """消費税計算のテスト"""
    generator = JournalGenerator(None)
    
    # 10%税込
    receipt = Receipt(total=1100, tax_rate=0.10)
    tax_amount, _ = generator._calculate_tax(receipt)
    assert tax_amount == 100
    
    # 8%税込
    receipt = Receipt(total=1080, tax_rate=0.08)
    tax_amount, _ = generator._calculate_tax(receipt)
    assert tax_amount == 74  # 端数切り捨て
    
    # 非課税
    receipt = Receipt(total=1000, tax_rate=0)
    tax_amount, _ = generator._calculate_tax(receipt)
    assert tax_amount == 0

def test_debit_account_determination(db):
    """借方勘定科目決定のテスト"""
    generator = JournalGenerator(db)
    
    # ベンダーマスタあり
    vendor = Vendor(
        name="スターバックス",
        name_norm="スターバックス",
        default_debit_account="5130"
    )
    receipt = Receipt(vendor_norm="スターバックス")
    account = generator._determine_debit_account(receipt, vendor)
    assert account == "5130"
    
    # 汎用ルール（交通費）
    receipt = Receipt(vendor_norm="jr東日本")
    account = generator._determine_debit_account(receipt, None)
    assert account == generator.default_accounts['expenses']['旅費交通費']
    
    # デフォルト
    receipt = Receipt(vendor_norm="不明なベンダー")
    account = generator._determine_debit_account(receipt, None)
    assert account == generator.default_accounts['expenses']['雑費']

def test_credit_account_determination(db):
    """貸方勘定科目決定のテスト"""
    generator = JournalGenerator(db)
    
    # 現金
    receipt = Receipt(payment_method=PaymentMethod.cash)
    account = generator._determine_credit_account(receipt, None)
    assert account == generator.default_accounts['assets']['現金']
    
    # クレジット
    receipt = Receipt(payment_method=PaymentMethod.credit)
    account = generator._determine_credit_account(receipt, None)
    assert account == generator.default_accounts['liabilities']['未払金']
    
    # デフォルト
    receipt = Receipt(payment_method=None)
    account = generator._determine_credit_account(receipt, None)
    assert account == generator.default_accounts['liabilities']['未払金']

def test_journal_generation(db):
    """仕訳生成の総合テスト"""
    generator = JournalGenerator(db)
    
    receipt = Receipt(
        id=1,
        video_id=1,
        vendor="スターバックス",
        vendor_norm="スターバックス",
        total=1100,
        tax_rate=0.10,
        payment_method=PaymentMethod.cash
    )
    
    entries = generator.generate_journal_entries(receipt)
    
    assert len(entries) == 3  # 本体、消費税、支払の3行
    
    # 本体
    assert entries[0].debit_amount == 1000
    assert entries[0].credit_amount == 0
    
    # 消費税
    assert entries[1].debit_amount == 100
    assert entries[1].credit_amount == 0
    
    # 支払
    assert entries[2].debit_amount == 0
    assert entries[2].credit_amount == 1100

if __name__ == "__main__":
    pytest.main([__file__])