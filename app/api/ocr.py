"""
OCR API endpoints for financial document recognition
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import base64
import io
from PIL import Image
import json

from ..services.ocr_service import ocr_service
from ..database.database import get_db
from ..models.user import User
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/upload-image/{user_id}")
async def upload_financial_image(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process financial document image
    
    Supported formats: JPG, PNG, JPEG
    Max file size: 10MB
    
    Returns extracted financial information in structured format
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="文件必须是图片格式")
        
        # Validate file size (10MB limit)
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        content = await file.read()
        if len(content) > MAX_SIZE:
            raise HTTPException(status_code=400, detail="图片大小不能超过10MB")
        
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # Convert image to base64
        image_base64 = base64.b64encode(content).decode('utf-8')
        
        # Process image with OCR service
        result = await ocr_service.process_financial_image(image_base64, user_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "图片处理成功",
                "data": result,
                "user_id": user_id,
                "filename": file.filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理图片失败: {str(e)}")

@router.post("/process-text/{user_id}")
async def process_financial_text(
    user_id: int,
    text_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Process financial text information directly
    
    Format:
    {
        "text": "financial text content",
        "account_type": "bank|broker|alipay|wechat|other",
        "additional_info": {}
    }
    """
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        text_content = text_data.get("text", "")
        account_type = text_data.get("account_type", "unknown")
        
        if not text_content:
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        # Create mock extracted info for text processing
        extracted_info = {
            "account_type": account_type,
            "extracted_text": text_content,
            "confidence": 0.9,
            "notes": "直接文本输入"
        }
        
        # Process according to account type
        if account_type == "bank":
            parsed_data = ocr_service.parse_bank_statement(extracted_info)
        elif account_type == "broker":
            parsed_data = ocr_service.parse_broker_statement(extracted_info)
        elif account_type in ["alipay", "wechat"]:
            parsed_data = ocr_service.parse_mobile_payment(extracted_info)
        else:
            parsed_data = {
                "type": "text_input",
                "raw_text": text_content,
                "account_type": account_type
            }
        
        result = {
            "status": "success",
            "extracted_info": extracted_info,
            "parsed_data": parsed_data,
            "confidence": 0.9,
            "suggestions": ocr_service._generate_import_suggestions(parsed_data)
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "文本处理成功",
                "data": result,
                "user_id": user_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文本失败: {str(e)}")

@router.get("/import-suggestions/{user_id}")
async def get_import_suggestions(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get data import suggestions and templates
    """
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        suggestions = {
            "image_types": {
                "bank": {
                    "name": "银行账户",
                    "description": "银行卡余额、储蓄账户等",
                    "examples": ["工商银行APP截图", "建设银行网银截图", "银行卡余额页面"],
                    "extract_fields": ["银行名称", "账户类型", "余额", "可用余额", "账号"]
                },
                "broker": {
                    "name": "券商账户",
                    "description": "股票、基金持仓信息",
                    "examples": ["老虎证券持仓", "雪球组合截图", "券商APP持仓页面"],
                    "extract_fields": ["券商名称", "持仓股票", "数量", "当前价格", "市值", "盈亏"]
                },
                "alipay": {
                    "name": "支付宝",
                    "description": "支付宝余额、余额宝等",
                    "examples": ["支付宝首页", "余额宝页面", "花呗页面"],
                    "extract_fields": ["余额", "余额宝金额", "花呗额度", "借呗额度"]
                },
                "wechat": {
                    "name": "微信支付",
                    "description": "微信钱包余额、理财等",
                    "examples": ["微信钱包页面", "微信理财页面", "零钱页面"],
                    "extract_fields": ["零钱余额", "理财金额", "信用卡还款"]
                }
            },
            "prompt_template": ocr_service.get_financial_info_prompt(),
            "supported_formats": ["JPG", "PNG", "JPEG"],
            "max_file_size": "10MB",
            "tips": [
                "确保图片清晰，文字可读",
                "包含完整的账户信息和余额",
                "避免个人敏感信息过度暴露",
                "可以多次上传不同类型的账户信息"
            ]
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": suggestions,
                "user_id": user_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取建议失败: {str(e)}")

@router.post("/import-data/{user_id}")
async def import_extracted_data(
    user_id: int,
    import_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Import extracted financial data into user's portfolio
    
    Format:
    {
        "data_type": "bank|broker|mobile_payment",
        "parsed_data": {...},
        "confirm_import": true
    }
    """
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        data_type = import_data.get("data_type")
        parsed_data = import_data.get("parsed_data", {})
        confirm_import = import_data.get("confirm_import", False)
        
        if not confirm_import:
            raise HTTPException(status_code=400, detail="请确认导入数据")
        
        # Import logic based on data type
        import_result = {"success": False, "message": ""}
        
        if data_type == "broker":
            # Import broker holdings
            holdings = parsed_data.get("holdings", [])
            imported_count = 0
            
            for holding in holdings:
                # This would integrate with our existing holdings API
                # For now, we'll just simulate the import
                imported_count += 1
            
            import_result = {
                "success": True,
                "message": f"成功导入 {imported_count} 个持仓",
                "imported_items": imported_count
            }
            
        elif data_type == "bank":
            # Import bank account as cash holding
            bank_name = parsed_data.get("bank_name", "未知银行")
            balance = parsed_data.get("balance", 0)
            
            import_result = {
                "success": True,
                "message": f"成功导入 {bank_name} 账户，余额: {balance}",
                "imported_items": 1
            }
            
        elif data_type == "mobile_payment":
            # Import mobile payment as cash equivalent
            platform = parsed_data.get("platform", "未知平台")
            balance = parsed_data.get("balance", 0)
            
            import_result = {
                "success": True,
                "message": f"成功导入 {platform} 账户，余额: {balance}",
                "imported_items": 1
            }
            
        else:
            raise HTTPException(status_code=400, detail="不支持的数据类型")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "数据导入成功",
                "data": import_result,
                "user_id": user_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入数据失败: {str(e)}")

@router.get("/demo-prompts")
async def get_demo_prompts():
    """
    Get demo prompts for different types of financial documents
    """
    demo_prompts = {
        "bank_statement": {
            "title": "银行账户识别示例",
            "description": "识别银行账户余额信息",
            "sample_prompt": ocr_service.get_financial_info_prompt(),
            "expected_output": {
                "account_type": "bank",
                "institution_name": "中国工商银行",
                "account_info": {
                    "account_holder": "张三",
                    "account_number": "****1234",
                    "account_id": "622202****"
                },
                "balance_info": {
                    "total_balance": "50000.00",
                    "available_balance": "48000.00",
                    "currency": "CNY",
                    "update_time": "2024-01-08"
                }
            }
        },
        "broker_statement": {
            "title": "券商持仓识别示例",
            "description": "识别股票/基金持仓信息",
            "sample_prompt": ocr_service.get_financial_info_prompt(),
            "expected_output": {
                "account_type": "broker",
                "institution_name": "老虎证券",
                "holdings": [
                    {
                        "symbol": "AAPL",
                        "name": "苹果公司",
                        "shares": "100",
                        "current_price": "180.00",
                        "market_value": "18000.00",
                        "cost_basis": "170.00",
                        "pnl": "1000.00",
                        "pnl_percent": "5.88"
                    }
                ]
            }
        }
    }
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": demo_prompts
        }
    ) 