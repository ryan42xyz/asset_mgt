"""
OCR Service for extracting financial information from images
"""

import base64
import json
import re
from typing import Dict, List, Any, Optional
from decimal import Decimal
import httpx
from ..config import settings
from ..database.redis_client import redis_client


class OCRService:
    """OCR Service for financial document recognition"""
    
    def __init__(self):
        pass
    
    def get_financial_info_prompt(self) -> str:
        """Get prompt for financial information extraction"""
        return """
你是一个专业的金融信息提取助手。请分析这张图片，提取其中的金融相关信息，并按照以下JSON格式返回：

{
  "account_type": "bank|alipay|wechat|broker|credit_card|other",
  "institution_name": "机构名称",
  "account_info": {
    "account_holder": "账户持有人姓名",
    "account_number": "账号/卡号（如果可见）",
    "account_id": "账户标识"
  },
  "balance_info": {
    "total_balance": "总余额数字",
    "available_balance": "可用余额数字", 
    "currency": "CNY|USD|其他货币",
    "update_time": "余额更新时间"
  },
  "holdings": [
    {
      "symbol": "股票/基金代码",
      "name": "股票/基金名称",
      "shares": "持有数量",
      "current_price": "当前价格",
      "market_value": "市值",
      "cost_basis": "成本价",
      "pnl": "盈亏金额",
      "pnl_percent": "盈亏百分比"
    }
  ],
  "extracted_text": "提取到的所有文本内容",
  "confidence": "识别置信度 0-1",
  "notes": "其他说明或注意事项"
}

识别规则：
1. 如果是银行卡/存款：account_type="bank"，重点提取余额信息
2. 如果是支付宝：account_type="alipay"，提取余额和理财信息
3. 如果是微信支付：account_type="wechat"，提取钱包余额
4. 如果是券商/股票账户：account_type="broker"，重点提取持仓信息
5. 如果是信用卡：account_type="credit_card"，提取可用额度和欠款
6. 金额数字请只返回数字，不要包含货币符号
7. 如果某些信息不可见或不确定，请设为null
8. 请确保返回有效的JSON格式

请仔细分析图片中的所有文字和数字信息。
"""
    
    async def extract_financial_info_with_llm(self, image_data: str, provider: str = "openai") -> Dict[str, Any]:
        """Use LLM to extract financial information from image"""
        try:
            prompt = self.get_financial_info_prompt()
            
            # 这里集成LLM API调用
            # 由于我们已有LLM工具，这里模拟返回结构
            mock_response = {
                "account_type": "broker",
                "institution_name": "示例券商",
                "account_info": {
                    "account_holder": "张三",
                    "account_number": "****1234",
                    "account_id": "ACC001"
                },
                "balance_info": {
                    "total_balance": "50000.00",
                    "available_balance": "45000.00",
                    "currency": "CNY",
                    "update_time": "2024-01-08"
                },
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
                ],
                "extracted_text": "这里是从图片中提取的所有文本",
                "confidence": 0.85,
                "notes": "这是一个模拟的识别结果，实际使用时会调用真实的LLM API"
            }
            
            return mock_response
            
        except Exception as e:
            return {
                "error": f"提取失败: {str(e)}",
                "confidence": 0.0
            }
    
    def parse_bank_statement(self, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse bank statement information"""
        if extracted_info.get("account_type") != "bank":
            return {"error": "不是银行账户信息"}
        
        return {
            "type": "bank_account",
            "bank_name": extracted_info.get("institution_name"),
            "account_holder": extracted_info.get("account_info", {}).get("account_holder"),
            "account_number": extracted_info.get("account_info", {}).get("account_number"),
            "balance": float(extracted_info.get("balance_info", {}).get("total_balance", 0)),
            "currency": extracted_info.get("balance_info", {}).get("currency", "CNY"),
            "update_time": extracted_info.get("balance_info", {}).get("update_time")
        }
    
    def parse_broker_statement(self, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse broker/securities account information"""
        if extracted_info.get("account_type") != "broker":
            return {"error": "不是券商账户信息"}
        
        holdings = []
        for holding in extracted_info.get("holdings", []):
            if holding.get("symbol") and holding.get("shares"):
                holdings.append({
                    "symbol": holding["symbol"],
                    "name": holding.get("name", ""),
                    "shares": float(holding["shares"]),
                    "current_price": float(holding.get("current_price", 0)),
                    "market_value": float(holding.get("market_value", 0)),
                    "cost_basis": float(holding.get("cost_basis", 0))
                })
        
        return {
            "type": "broker_account",
            "broker_name": extracted_info.get("institution_name"),
            "account_holder": extracted_info.get("account_info", {}).get("account_holder"),
            "account_number": extracted_info.get("account_info", {}).get("account_number"),
            "total_balance": float(extracted_info.get("balance_info", {}).get("total_balance", 0)),
            "holdings": holdings,
            "currency": extracted_info.get("balance_info", {}).get("currency", "USD")
        }
    
    def parse_mobile_payment(self, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse mobile payment (Alipay/WeChat) information"""
        account_type = extracted_info.get("account_type")
        if account_type not in ["alipay", "wechat"]:
            return {"error": "不是支付宝或微信信息"}
        
        platform_name = "支付宝" if account_type == "alipay" else "微信支付"
        
        return {
            "type": "mobile_payment",
            "platform": platform_name,
            "account_holder": extracted_info.get("account_info", {}).get("account_holder"),
            "balance": float(extracted_info.get("balance_info", {}).get("total_balance", 0)),
            "available_balance": float(extracted_info.get("balance_info", {}).get("available_balance", 0)),
            "currency": extracted_info.get("balance_info", {}).get("currency", "CNY"),
            "update_time": extracted_info.get("balance_info", {}).get("update_time")
        }
    
    async def process_financial_image(self, image_data: str, user_id: int) -> Dict[str, Any]:
        """Process financial image and extract structured information"""
        try:
            # Step 1: Extract information using LLM
            extracted_info = await self.extract_financial_info_with_llm(image_data)
            
            if "error" in extracted_info:
                return extracted_info
            
            # Step 2: Parse according to account type
            account_type = extracted_info.get("account_type")
            
            if account_type == "bank":
                parsed_data = self.parse_bank_statement(extracted_info)
            elif account_type == "broker":
                parsed_data = self.parse_broker_statement(extracted_info)
            elif account_type in ["alipay", "wechat"]:
                parsed_data = self.parse_mobile_payment(extracted_info)
            else:
                parsed_data = {
                    "type": "unknown",
                    "raw_data": extracted_info
                }
            
            # Step 3: Cache the result
            cache_key = f"ocr_result:{user_id}:{hash(image_data)}"
            redis_client.set(cache_key, {
                "extracted_info": extracted_info,
                "parsed_data": parsed_data,
                "processed_at": "2024-01-08T00:00:00"
            }, ttl=3600)
            
            return {
                "status": "success",
                "extracted_info": extracted_info,
                "parsed_data": parsed_data,
                "confidence": extracted_info.get("confidence", 0),
                "suggestions": self._generate_import_suggestions(parsed_data)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"处理图片失败: {str(e)}"
            }
    
    def _generate_import_suggestions(self, parsed_data: Dict[str, Any]) -> List[str]:
        """Generate suggestions for importing the data"""
        suggestions = []
        
        data_type = parsed_data.get("type")
        
        if data_type == "broker_account":
            suggestions.extend([
                "检测到券商账户信息",
                f"发现 {len(parsed_data.get('holdings', []))} 个持仓",
                "建议导入到投资组合模块",
                "可以自动更新持仓数据"
            ])
        elif data_type == "bank_account":
            suggestions.extend([
                "检测到银行账户信息",
                f"账户余额: {parsed_data.get('balance', 0)} {parsed_data.get('currency', 'CNY')}",
                "建议添加到现金资产类别",
                "可以设置自动同步"
            ])
        elif data_type == "mobile_payment":
            suggestions.extend([
                f"检测到{parsed_data.get('platform')}账户信息",
                f"余额: {parsed_data.get('balance', 0)} {parsed_data.get('currency', 'CNY')}",
                "建议添加到现金等价物",
                "可以定期更新余额"
            ])
        
        return suggestions


# Global OCR service instance
ocr_service = OCRService() 