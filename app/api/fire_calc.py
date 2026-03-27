"""
FIRE (Financial Independence, Retire Early) Calculator API
"""

import math
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/fire", tags=["FIRE Calculator"])


class FireCalcRequest(BaseModel):
    """FIRE计算器输入参数"""
    principal: float = Field(..., description="初始本金 (USD)")
    monthly_contribution: float = Field(..., description="月定投额 (USD)")
    annual_return: float = Field(..., description="年化收益率 (如0.04表示4%)")
    monthly_spending: float = Field(..., description="财务自由后月支出 (USD)")
    withdrawal_rate: float = Field(0.04, description="安全提取率 (默认4%)")
    start_date: Optional[str] = Field(None, description="起始日期 (YYYY-MM-DD)")
    contribution_timing: str = Field("end", description="定投时机: 'begin'(月初) 或 'end'(月末)")


class FireCalcResponse(BaseModel):
    """FIRE计算器输出结果"""
    target_amount: float
    months_to_fi: int
    years_to_fi: float
    target_date: Optional[str]
    annual_projection: List[Dict[str, Any]]
    milestones: Dict[str, Dict[str, Any]]
    sensitivity_analysis: Dict[str, Any]


def calculate_monthly_return(annual_return: float) -> float:
    """将年化收益率转换为月化收益率"""
    return (1 + annual_return) ** (1/12) - 1


def calculate_months_to_fi(
    principal: float,
    monthly_contribution: float,
    monthly_return: float,
    target_amount: float,
    contribution_timing: str = "end"
) -> int:
    """
    计算达到财务自由目标所需的月份数
    
    使用闭式解公式：
    FV = P*(1+r)^n + S*((1+r)^n - 1)/r
    
    其中：
    - FV: 目标金额
    - P: 初始本金
    - S: 月定投额
    - r: 月化收益率
    - n: 所需月份数
    """
    if monthly_return == 0:
        # 无收益情况下的简单计算
        return math.ceil((target_amount - principal) / monthly_contribution)
    
    if contribution_timing == "begin":
        # 月初定投：FV = P*(1+r)^n + S*(1+r)*((1+r)^n - 1)/r
        numerator = target_amount + (monthly_contribution * (1 + monthly_return) / monthly_return)
        denominator = principal + (monthly_contribution * (1 + monthly_return) / monthly_return)
    else:
        # 月末定投：FV = P*(1+r)^n + S*((1+r)^n - 1)/r
        numerator = target_amount + (monthly_contribution / monthly_return)
        denominator = principal + (monthly_contribution / monthly_return)
    
    if denominator <= 0:
        raise ValueError("Invalid parameters: denominator must be positive")
    
    ratio = numerator / denominator
    if ratio <= 0:
        raise ValueError("Invalid parameters: ratio must be positive")
    
    months = math.log(ratio) / math.log(1 + monthly_return)
    return max(0, math.ceil(months))


def generate_annual_projection(
    principal: float,
    monthly_contribution: float,
    monthly_return: float,
    target_amount: float,
    months_to_fi: int,
    contribution_timing: str = "end",
    projection_years: int = 30,
    monthly_spending: float = 0
) -> List[Dict[str, Any]]:
    """生成年度资产增长预测表（30年）- 优化版本"""
    projection = []
    balance = principal
    total_contributed = principal
    total_return = 0
    total_spending = 0
    
    # 记录上一年的数据，用于计算当年变化
    prev_year_balance = principal
    prev_year_contributed = principal
    prev_year_return = 0
    prev_year_spending = 0
    
    # 计算总月数（30年）
    total_months = projection_years * 12
    
    for month in range(1, total_months + 1):
        # 检查是否已达到目标净值
        fi_reached = balance >= target_amount
        
        # 月初定投（仅在未达到目标时）
        if contribution_timing == "begin" and not fi_reached:
            balance += monthly_contribution
            total_contributed += monthly_contribution
        
        # 月度收益
        monthly_gain = balance * monthly_return
        balance += monthly_gain
        total_return += monthly_gain
        
        # 月末定投（仅在未达到目标时）
        if contribution_timing == "end" and not fi_reached:
            balance += monthly_contribution
            total_contributed += monthly_contribution
        
        # 支出（仅在达到财务自由后）
        if fi_reached:
            balance -= monthly_spending
            total_spending += monthly_spending
        
        # 记录年末数据
        if month % 12 == 0:
            year = month // 12
            
            # 计算当年变化
            year_contribution = total_contributed - prev_year_contributed
            year_return = total_return - prev_year_return
            year_spending = total_spending - prev_year_spending
            
            # 计算真实累计收益（修正口径）
            real_total_return = balance + total_spending - total_contributed
            
            # 计算目标完成度
            target_percentage = (balance / target_amount * 100)
            
            projection.append({
                "year": year,
                "balance": round(balance, 2),
                "target_percentage": round(target_percentage, 2),
                "total_contributed": round(total_contributed, 2),
                "total_spending": round(total_spending, 2),
                "real_total_return": round(real_total_return, 2),
                "year_contribution": round(year_contribution, 2),
                "year_spending": round(year_spending, 2),
                "year_return": round(year_return, 2),
                "fi_reached": balance >= target_amount
            })
            
            # 更新上一年数据
            prev_year_balance = balance
            prev_year_contributed = total_contributed
            prev_year_return = total_return
            prev_year_spending = total_spending
    
    return projection


def calculate_milestones(
    principal: float,
    monthly_contribution: float,
    monthly_return: float,
    target_amount: float,
    contribution_timing: str = "end"
) -> Dict[str, Dict[str, Any]]:
    """计算关键里程碑"""
    milestones = {}
    milestone_percentages = [0.25, 0.5, 0.75, 0.9, 0.95, 1.0]
    
    for percentage in milestone_percentages:
        milestone_amount = target_amount * percentage
        try:
            months = calculate_months_to_fi(
                principal, monthly_contribution, monthly_return, 
                milestone_amount, contribution_timing
            )
            years = months / 12
            
            # 计算达到里程碑时的资产构成
            balance = principal
            total_contributed = principal
            
            for month in range(1, months + 1):
                if contribution_timing == "begin":
                    balance += monthly_contribution
                    total_contributed += monthly_contribution
                
                balance *= (1 + monthly_return)
                
                if contribution_timing == "end":
                    balance += monthly_contribution
                    total_contributed += monthly_contribution
            
            total_return = balance - total_contributed
            
            milestones[f"{int(percentage * 100)}%"] = {
                "amount": round(milestone_amount, 2),
                "months": months,
                "years": round(years, 2),
                "total_contributed": round(total_contributed, 2),
                "total_return": round(total_return, 2),
                "return_contribution_ratio": round(total_return / total_contributed, 4) if total_contributed > 0 else 0
            }
        except ValueError:
            # 如果无法达到某个里程碑，跳过
            continue
    
    return milestones


def generate_sensitivity_analysis(
    principal: float,
    monthly_contribution: float,
    annual_return: float,
    monthly_spending: float,
    withdrawal_rate: float,
    contribution_timing: str = "end"
) -> Dict[str, Any]:
    """生成敏感性分析"""
    base_target = (monthly_spending * 12) / withdrawal_rate
    base_monthly_return = calculate_monthly_return(annual_return)
    base_months = calculate_months_to_fi(
        principal, monthly_contribution, base_monthly_return, 
        base_target, contribution_timing
    )
    
    sensitivity = {
        "base_case": {
            "annual_return": annual_return,
            "monthly_contribution": monthly_contribution,
            "monthly_spending": monthly_spending,
            "months": base_months,
            "years": round(base_months / 12, 2)
        },
        "return_scenarios": [],
        "contribution_scenarios": [],
        "spending_scenarios": []
    }
    
    # 收益率敏感性 (±1%)
    for return_change in [-0.01, -0.005, 0.005, 0.01]:
        new_return = annual_return + return_change
        if new_return > 0:
            new_monthly_return = calculate_monthly_return(new_return)
            try:
                new_months = calculate_months_to_fi(
                    principal, monthly_contribution, new_monthly_return,
                    base_target, contribution_timing
                )
                sensitivity["return_scenarios"].append({
                    "annual_return": new_return,
                    "months": new_months,
                    "years": round(new_months / 12, 2),
                    "change_months": new_months - base_months
                })
            except ValueError:
                continue
    
    # 定投额敏感性 (±10%)
    for contrib_change in [-0.1, -0.05, 0.05, 0.1]:
        new_contribution = monthly_contribution * (1 + contrib_change)
        if new_contribution > 0:
            try:
                new_months = calculate_months_to_fi(
                    principal, new_contribution, base_monthly_return,
                    base_target, contribution_timing
                )
                sensitivity["contribution_scenarios"].append({
                    "monthly_contribution": new_contribution,
                    "months": new_months,
                    "years": round(new_months / 12, 2),
                    "change_months": new_months - base_months
                })
            except ValueError:
                continue
    
    # 支出敏感性 (±10%)
    for spending_change in [-0.1, -0.05, 0.05, 0.1]:
        new_spending = monthly_spending * (1 + spending_change)
        new_target = (new_spending * 12) / withdrawal_rate
        if new_target > 0:
            try:
                new_months = calculate_months_to_fi(
                    principal, monthly_contribution, base_monthly_return,
                    new_target, contribution_timing
                )
                sensitivity["spending_scenarios"].append({
                    "monthly_spending": new_spending,
                    "target_amount": new_target,
                    "months": new_months,
                    "years": round(new_months / 12, 2),
                    "change_months": new_months - base_months
                })
            except ValueError:
                continue
    
    return sensitivity


@router.post("/calculate", response_model=FireCalcResponse)
async def calculate_fire(request: FireCalcRequest) -> FireCalcResponse:
    """
    计算达到财务自由所需的时间
    
    输入参数：
    - principal: 初始本金
    - monthly_contribution: 月定投额
    - annual_return: 年化收益率
    - monthly_spending: 月支出
    - withdrawal_rate: 安全提取率
    - start_date: 起始日期
    - contribution_timing: 定投时机
    """
    try:
        # 计算目标金额
        target_amount = (request.monthly_spending * 12) / request.withdrawal_rate
        
        # 计算月化收益率
        monthly_return = calculate_monthly_return(request.annual_return)
        
        # 计算所需月份
        months_to_fi = calculate_months_to_fi(
            request.principal,
            request.monthly_contribution,
            monthly_return,
            target_amount,
            request.contribution_timing
        )
        
        # 计算目标日期
        target_date = None
        if request.start_date:
            try:
                start = datetime.strptime(request.start_date, "%Y-%m-%d").date()
                target_date = start.replace(year=start.year + months_to_fi // 12)
                # 简单处理月份偏移
                month_offset = months_to_fi % 12
                if month_offset > 0:
                    target_date = target_date.replace(month=min(12, start.month + month_offset))
            except ValueError:
                pass
        
        # 生成年度预测（30年）
        annual_projection = generate_annual_projection(
            request.principal,
            request.monthly_contribution,
            monthly_return,
            target_amount,
            months_to_fi,
            request.contribution_timing,
            projection_years=30,
            monthly_spending=request.monthly_spending
        )
        
        # 计算里程碑
        milestones = calculate_milestones(
            request.principal,
            request.monthly_contribution,
            monthly_return,
            target_amount,
            request.contribution_timing
        )
        
        # 生成敏感性分析
        sensitivity_analysis = generate_sensitivity_analysis(
            request.principal,
            request.monthly_contribution,
            request.annual_return,
            request.monthly_spending,
            request.withdrawal_rate,
            request.contribution_timing
        )
        
        return FireCalcResponse(
            target_amount=round(target_amount, 2),
            months_to_fi=months_to_fi,
            years_to_fi=round(months_to_fi / 12, 2),
            target_date=target_date.isoformat() if target_date else None,
            annual_projection=annual_projection,
            milestones=milestones,
            sensitivity_analysis=sensitivity_analysis
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@router.get("/example")
async def get_example_calculation() -> FireCalcResponse:
    """获取示例计算结果"""
    example_request = FireCalcRequest(
        principal=100000,
        monthly_contribution=2400,
        annual_return=0.04,
        monthly_spending=1400,
        withdrawal_rate=0.04,
        start_date="2025-08-01"
    )
    
    return await calculate_fire(example_request)
