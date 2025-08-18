from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Vendor, Account, Rule
from schemas import VendorCreate, VendorResponse, AccountCreate, AccountResponse, RuleCreate, RuleResponse

router = APIRouter()

# Vendor endpoints
@router.get("/vendors", response_model=List[VendorResponse])
async def list_vendors(db: Session = Depends(get_db)):
    """ベンダー一覧取得"""
    vendors = db.query(Vendor).all()
    return vendors

@router.post("/vendors", response_model=VendorResponse)
async def create_vendor(vendor: VendorCreate, db: Session = Depends(get_db)):
    """ベンダー登録"""
    # 正規化
    import re
    name_norm = re.sub(r'[^\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '', vendor.name).lower()
    
    db_vendor = Vendor(
        name=vendor.name,
        name_norm=name_norm,
        default_debit_account=vendor.default_debit_account,
        default_credit_account=vendor.default_credit_account,
        default_tax_rate=vendor.default_tax_rate,
        default_payment_method=vendor.default_payment_method
    )
    
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    
    return db_vendor

@router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: int, db: Session = Depends(get_db)):
    """ベンダー削除"""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(404, "ベンダーが見つかりません")
    
    db.delete(vendor)
    db.commit()
    
    return {"message": "ベンダーを削除しました"}

# Account endpoints
@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(db: Session = Depends(get_db)):
    """勘定科目一覧取得"""
    accounts = db.query(Account).filter(Account.is_active == True).all()
    return accounts

@router.post("/accounts", response_model=AccountResponse)
async def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    """勘定科目登録"""
    db_account = Account(
        code=account.code,
        name=account.name,
        type=account.type,
        tax_category=account.tax_category
    )
    
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    return db_account

# Rule endpoints
@router.get("/rules", response_model=List[RuleResponse])
async def list_rules(db: Session = Depends(get_db)):
    """仕訳ルール一覧取得"""
    rules = db.query(Rule).filter(Rule.is_active == True).order_by(Rule.priority.desc()).all()
    return rules

@router.post("/rules", response_model=RuleResponse)
async def create_rule(rule: RuleCreate, db: Session = Depends(get_db)):
    """仕訳ルール登録"""
    db_rule = Rule(
        pattern=rule.pattern,
        pattern_type=rule.pattern_type,
        debit_account=rule.debit_account,
        credit_account=rule.credit_account,
        tax_rate=rule.tax_rate,
        priority=rule.priority
    )
    
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    
    return db_rule

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """仕訳ルール削除"""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "ルールが見つかりません")
    
    rule.is_active = False
    db.commit()
    
    return {"message": "ルールを無効化しました"}