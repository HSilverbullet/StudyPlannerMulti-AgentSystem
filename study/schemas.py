from typing import List, Optional
from pydantic import BaseModel, Field
from typing import Dict, Any

class StudyRequest(BaseModel):
    """学习规划请求"""
    learner_name: str = Field(default="学习者")
    subject: str = Field(..., description="学习主题/科目，例如：Python、数学、英语口语、考研政治")
    goal: str = Field(..., description="学习目标，例如：通过某考试/掌握某技能/完成某项目")
    current_level: str = Field(..., description="自述当前水平，例如：零基础/入门/中级/有基础但不系统")
    deadline: Optional[str] = Field(default=None, description="截止日期(YYYY-MM-DD)，没有可不填")
    study_days: int = Field(..., description="计划学习总天数")
    daily_time_minutes: int = Field(..., description="每天可用学习时长（分钟）")

    preferences: List[str] = Field(default_factory=list, description="偏好，例如：视频/文章/刷题/项目驱动")
    constraints: List[str] = Field(default_factory=list, description="限制条件，例如：工作日只能晚上/不想看长视频")
    free_text_input: Optional[str] = Field(default=None, description="额外要求")


class ResourceItem(BaseModel):
    title: str
    url: str
    type: str = Field(default="article", description="article/video/course/book/tool")
    summary: str = Field(default="")
    difficulty: str = Field(default="unknown", description="beginner/intermediate/advanced/unknown")


class DailyPlan(BaseModel):
    day: int
    date: Optional[str] = None
    total_minutes: int
    focus: str
    tasks: List[str]
    resources: List[ResourceItem] = Field(default_factory=list)
    checkpoint: str = Field(default="", description="当天验收标准/输出物")


class StudyPlan(BaseModel):
    subject: str
    goal: str
    learner_profile: Dict[str, Any]
    diagnosis: Dict[str, Any]
    time_plan: Dict[str, Any]
    recommended_resources: List[ResourceItem]
    daily_plans: List[DailyPlan]
    milestones: List[str]
    risks_and_mitigations: List[str]

class StudyPlanResponse(BaseModel):
    """学习计划响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: Optional[StudyPlan] = Field(default=None, description="学习计划数据")

