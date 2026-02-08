import json
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .my_llm import llm1
from langchain.agents import create_agent
from .prompts import (
    DIAGNOSIS_AGENT_PROMPT,
    RESOURCE_AGENT_PROMPT,  
    TIME_AGENT_PROMPT,
    STUDY_PLANNER_AGENT_PROMPT
)
from .schemas import StudyRequest, StudyPlan, StudyPlanResponse
# 资源检索工具：示例用 DuckDuckGo（不需要 key）
# 如果你已有 MCP Web Search 工具，请看下面“如何替换成 MCP 搜索工具”
try:
    from langchain_community.tools import DuckDuckGoSearchRun
except Exception:
    DuckDuckGoSearchRun = None



class MultiAgentStudyPlanner:
    """多智能体学习规划系统"""

    def __init__(self):
        self.llm = llm1
        self.diagnosis_agent = None
        self.resource_agent = None
        self.time_agent = None
        self.planner_agent = None

        self.resource_tools = []

    async def initialize(self):
        """初始化多智能体系统"""
        print("初始化多智能体学习规划系统...")

        # 资源检索工具：示例用 DuckDuckGo
        if DuckDuckGoSearchRun is not None:
            self.resource_tools = [DuckDuckGoSearchRun()]
        else:
            self.resource_tools = []

        print("  - 创建学情诊断Agent...")
        self.diagnosis_agent = create_agent(
            self.llm,
            tools=[],  # 诊断不一定需要工具
            system_prompt=DIAGNOSIS_AGENT_PROMPT
        )

        print("  - 创建资源检索Agent...")
        self.resource_agent = create_agent(
            self.llm,
            tools=self.resource_tools,  # 有搜索工具才真正“联网搜”
            system_prompt=RESOURCE_AGENT_PROMPT
        )

        print("  - 创建时间规划Agent...")
        self.time_agent = create_agent(
            self.llm,
            tools=[],
            system_prompt=TIME_AGENT_PROMPT
        )

        print("  - 创建学习规划Agent...")
        self.planner_agent = create_agent(
            self.llm,
            tools=[],
            system_prompt=STUDY_PLANNER_AGENT_PROMPT
        )

        print("✅ 多智能体学习规划系统初始化成功")
        print(f"   资源检索工具数量: {len(self.resource_tools)}")
        if self.resource_tools:
            print(f"   可用工具: {[t.name for t in self.resource_tools]}")
        else:
            print("   ⚠️ 未检测到联网搜索工具，资源Agent将只能基于输入文本给建议（不会真正搜索链接）")

    async def plan_study(self, request: StudyRequest) -> StudyPlan:
        """
        使用多智能体进行学习规划
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作生成学习规划...")
            print(f"学习主题: {request.subject}")
            print(f"目标: {request.goal}")
            print(f"当前水平: {request.current_level}")
            print(f"学习天数: {request.study_days} 天")
            print(f"每日时长: {request.daily_time_minutes} 分钟")
            print(f"{'='*60}\n")

            # 1) 诊断
            print("🧠 步骤1: 学情诊断...")
            diagnosis_query = self._build_diagnosis_query(request)
            diagnosis_resp = await self.diagnosis_agent.ainvoke(diagnosis_query)
            diagnosis_text = self._extract_text(diagnosis_resp)
            print(f"学情诊断结果: {diagnosis_text[:260]}...\n")

            await asyncio.sleep(0.5)

            # 2) 资源搜索
            print("🔎 步骤2: 搜索学习资源...")
            resource_query = self._build_resource_query(request, diagnosis_text)
            resource_resp = await self.resource_agent.ainvoke(resource_query)
            resource_text = self._extract_text(resource_resp)
            print(f"资源搜索结果: {resource_text[:260]}...\n")

            await asyncio.sleep(0.5)

            # 3) 时间规划
            print("⏳ 步骤3: 规划学习时间...")
            time_query = self._build_time_query(request)
            time_resp = await self.time_agent.ainvoke(time_query)
            time_text = self._extract_text(time_resp)
            print(f"时间规划建议: {time_text[:260]}...\n")

            await asyncio.sleep(0.5)

            # 4) 输出JSON学习计划
            print("📋 步骤4: 生成学习规划(JSON)...")
            planner_query = self._build_planner_query(request, diagnosis_text, resource_text, time_text)
            planner_input = {"messages": [("user", planner_query)]}
            # planner_resp = await self.planner_agent.ainvoke(planner_input)
            planner_resp = await self.planner_agent.ainvoke(planner_query)
            planner_text = self._extract_text(planner_resp)
            print(f"学习规划结果(截断): {planner_text[:900]}...\n")

            plan = self._parse_response(planner_text, request)
            print(f"{'='*60}")
            print(f"✅ 学习规划生成完成!")
            print(f"{'='*60}\n")

            return plan

        except Exception as e:
            print(f"❌ 学习规划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    # -------------------------
    # Query Builders
    # -------------------------

    def _build_diagnosis_query(self, request: StudyRequest) -> dict:
        preferences = "、".join(request.preferences) if request.preferences else "无"
        constraints = "、".join(request.constraints) if request.constraints else "无"
        extra = request.free_text_input or "无"

        return {
            "messages": [
                ("user",
                 f"""请对学习者进行学情诊断（输出结构化要点即可）：

- 学习主题/科目: {request.subject}
- 学习目标: {request.goal}
- 自述当前水平: {request.current_level}
- 学习天数: {request.study_days}天
- 每日可用时长: {request.daily_time_minutes}分钟
- 偏好: {preferences}
- 约束: {constraints}
- 额外要求: {extra}

请输出：
1) 当前水平判断（证据/依据写清楚，信息不足用“待确认”）
2) 知识结构拆解（从基础到进阶）
3) 薄弱点与优先级（高/中/低）
4) 建议的学习路线策略（例如：项目驱动/刷题驱动/听说读写均衡）
5) 需要进一步追问的问题（最多6个）
""")
            ]
        }

    def _build_resource_query(self, request: StudyRequest, diagnosis_text: str) -> dict:
        preferences = "、".join(request.preferences) if request.preferences else "无"
        return {
            "messages": [
                ("user",
                 f"""请联网搜索并推荐学习资源（8-14条为宜），并按“最推荐优先”排序：

主题: {request.subject}
目标: {request.goal}
学习者水平（诊断参考）:
{diagnosis_text}

偏好: {preferences}

输出格式建议：
- 标题：
- 链接：
- 类型(article/video/course/book/tool)：
- 难度(beginner/intermediate/advanced)：
- 推荐理由（1-2句）：

注意：
- 尽量提供可访问的真实链接
- 优先权威来源（官方文档、知名课程平台、经典教材）
""")
            ]
        }

    def _build_time_query(self, request: StudyRequest) -> dict:
        constraints = "、".join(request.constraints) if request.constraints else "无"
        extra = request.free_text_input or "无"

        return {
            "messages": [
                ("user",
                 f"""请为学习者生成时间规划建议（结构化要点即可）：

- 学习主题: {request.subject}
- 学习目标: {request.goal}
- 学习总天数: {request.study_days}天
- 每日可用时长: {request.daily_time_minutes}分钟
- 截止日期: {request.deadline or "无"}
- 约束条件: {constraints}
- 额外要求: {extra}

请输出：
1) 每日时间切分建议（例如：20%复习、50%新学、30%练习）
2) 阶段节奏（例如：第1周打基础、第2周强化练习…；若天数少也给阶段）
3) 复盘频率与方式
4) 风险与调整策略（至少3条）
""")
            ]
        }

    def _build_planner_query(self, request: StudyRequest, diagnosis: str, resources: str, time_plan: str) -> dict:
        pref = ", ".join(request.preferences) if request.preferences else "无"
        cons = ", ".join(request.constraints) if request.constraints else "无"
        extra = request.free_text_input or "无"
        
        return {
            "messages":[
                ("user", 
                 f"""请生成严格JSON，输出必须匹配 StudyPlanResponse（包含 success/message/data）。data 内部是 StudyPlan。

【基本信息】
- learner_name: {request.learner_name}
- subject: {request.subject}
- goal: {request.goal}
- current_level: {request.current_level}
- deadline: {request.deadline or ""}
- study_days: {request.study_days}
- daily_time_minutes: {request.daily_time_minutes}
- preferences: {pref}
- constraints: {cons}
- extra: {extra}

【学情诊断结果】
{diagnosis}

【资源Agent结果（只能从这里挑资源链接，不要编造链接）】
{resources}

【时间Agent结果】
{time_plan}

【硬性要求】
0) 只输出 JSON，不要 Markdown，不要解释，不要代码块
1) 输出结构必须是：{{"success": true, "message": "...", "data": {{...StudyPlan...}}}}
2) data.daily_plans 长度必须等于 study_days
3) 每天 tasks 3-8条，并与 total_minutes 匹配（不要超负荷）
4) checkpoint 必须可验收
5) data.recommended_resources 至少6条，且每条必须是 ResourceItem 对象（title/url/type/summary/difficulty 都要有）
6) data.daily_plans[i].resources 每条也必须是 ResourceItem 对象
7) data.milestones 必须是字符串数组 List[str]
8) data.risks_and_mitigations 必须是字符串数组 List[str]（不要输出 {{risk,mitigation}} 对象）
""")
            ]
        }
    
    def _wrap_resource(self, x: Any) -> Dict[str, Any]:
        """把 url(str)/dict 统一成 ResourceItem dict"""
        if isinstance(x, str):
            return {
                "title": x,
                "url": x,
                "type": "article",
                "summary": "",
                "difficulty": "unknown",
            }
        if isinstance(x, dict):
            url = x.get("url") or x.get("link") or x.get("href") or ""
            title = x.get("title") or x.get("name") or (url if url else "resource")
            return {
                "title": title,
                "url": url,
                "type": x.get("type", "article"),
                "summary": x.get("summary", ""),
                "difficulty": x.get("difficulty", "unknown"),
            }
        return {
            "title": "resource",
            "url": str(x),
            "type": "article",
            "summary": "",
            "difficulty": "unknown",
        }

    def _normalize_plan_response(self, raw: Dict[str, Any], request: StudyRequest) -> Dict[str, Any]:
        """把 LLM 输出兜底修成 StudyPlanResponse -> StudyPlan 可解析的结构"""
        # 1) 包一层 StudyPlanResponse（如果模型直接给了 StudyPlan）
        if "data" not in raw and "success" not in raw:
            raw = {"success": True, "message": "ok", "data": raw}

        raw.setdefault("success", True)
        raw.setdefault("message", "")

        data = raw.get("data") or {}
        raw["data"] = data

        # 2) StudyPlan 必填字段兜底
        data.setdefault("subject", request.subject)
        data.setdefault("goal", request.goal)

        data.setdefault("learner_profile", {
            "learner_name": request.learner_name,
            "current_level": request.current_level,
            "deadline": request.deadline,
            "preferences": request.preferences,
            "constraints": request.constraints,
            "free_text_input": request.free_text_input,
            "study_days": request.study_days,
            "daily_time_minutes": request.daily_time_minutes,
        })
        data.setdefault("diagnosis", {})
        data.setdefault("time_plan", {
            "study_days": request.study_days,
            "daily_time_minutes": request.daily_time_minutes,
            "deadline": request.deadline
        })

        # 3) recommended_resources -> ResourceItem[]
        rr = data.get("recommended_resources", []) or []
        data["recommended_resources"] = [self._wrap_resource(r) for r in rr]

        # 4) daily_plans 补齐 day/total_minutes/focus/tasks/resources/checkpoint
        dps = data.get("daily_plans", []) or []
        fixed = []
        for idx, dp in enumerate(dps, start=1):
            if not isinstance(dp, dict):
                dp = {"focus": str(dp)}

            dp.setdefault("day", idx)
            dp.setdefault("date", None)
            dp.setdefault("total_minutes", request.daily_time_minutes)
            dp.setdefault("focus", f"{request.subject} 第{dp['day']}天")
            dp.setdefault("checkpoint", "")

            # tasks: 必须 List[str]
            tasks = dp.get("tasks", [])
            if tasks is None:
                tasks = []
            if isinstance(tasks, str):
                tasks = [tasks]
            if not isinstance(tasks, list):
                tasks = [str(tasks)]
            if len(tasks) == 0:
                tasks = ["学习核心概念", "完成 1-2 个练习", "写总结/笔记"]
            dp["tasks"] = [str(t) for t in tasks]

            # resources: 必须 ResourceItem[]
            res = dp.get("resources", []) or []
            dp["resources"] = [self._wrap_resource(r) for r in res]

            fixed.append(dp)

        # 如果 LLM 没给 daily_plans 或数量不够，强制补齐到 study_days（否则必炸）
        if len(fixed) < request.study_days:
            for d in range(len(fixed) + 1, request.study_days + 1):
                fixed.append({
                    "day": d,
                    "date": None,
                    "total_minutes": request.daily_time_minutes,
                    "focus": f"{request.subject} 第{d}天",
                    "tasks": ["学习核心概念", "完成练习", "总结复盘"],
                    "resources": [],
                    "checkpoint": "输出一份可检验的笔记/练习结果"
                })
        # 如果超过了，截断
        if len(fixed) > request.study_days:
            fixed = fixed[:request.study_days]

        data["daily_plans"] = fixed

        # 5) milestones 必须 List[str]
        ms = data.get("milestones", []) or []
        if isinstance(ms, str):
            ms = [ms]
        if ms and isinstance(ms[0], dict):
            ms = [f"{m.get('day','')}: {m.get('criteria','')}".strip(": ").strip() for m in ms]
        data["milestones"] = [str(x) for x in ms]

        # 6) risks_and_mitigations 必须 List[str]
        ram = data.get("risks_and_mitigations", []) or []
        if isinstance(ram, str):
            ram = [ram]
        if ram and isinstance(ram[0], dict):
            ram = [f"{x.get('risk','风险')}：{x.get('mitigation','应对')}" for x in ram]
        data["risks_and_mitigations"] = [str(x) for x in ram]

        return raw

    # -------------------------
    # Parsing / Extraction
    # -------------------------

    def _parse_response(self, response: str, request: StudyRequest) -> StudyPlan:
        json_str = ""
        try:
            # 1) 提取 JSON
            if "```json" in response:
                json_str = response.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in response:
                parts = response.split("```")
                json_str = parts[1].strip() if len(parts) >= 3 else parts[-1].strip()
            else:
                start = response.find("{")
                if start == -1:
                    raise ValueError("未找到JSON起始 {")
                bracket_count = 0
                end = start
                for i, ch in enumerate(response[start:], start):
                    if ch == "{":
                        bracket_count += 1
                    elif ch == "}":
                        bracket_count -= 1
                        if bracket_count == 0:
                            end = i + 1
                            break
                if bracket_count != 0:
                    raise ValueError("JSON 大括号不匹配")
                json_str = response[start:end]

            json_str = json_str.strip()
            print(f"提取到的JSON(截断):\n{json_str[:600]}...\n")

            # 2) loads + normalize
            raw = json.loads(json_str)
            raw = self._normalize_plan_response(raw, request)

            # 3) 先用 StudyPlanResponse 校验更稳，再取 data
            parsed = StudyPlanResponse(**raw)
            if not parsed.success or parsed.data is None:
                raise ValueError(f"规划生成失败: {parsed.message}")
            return parsed.data

        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            print(f"问题JSON内容(截断):\n{json_str[:1200]}")
            raise
        except Exception as e:
            print(f"提取JSON失败: {e}")
            print(f"原始响应(截断):\n{response[:1200]}")
            raise


    def _extract_text(self, response) -> str:
        """从 Agent 响应中提取可读文本"""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            if "messages" in response:
                messages = response["messages"]
                if messages:
                    last_msg = messages[-1]
                    if hasattr(last_msg, "content"):
                        content = last_msg.content
                        if isinstance(content, str):
                            return content
                        if isinstance(content, list):
                            return "".join([
                                c.get("text", "")
                                for c in content
                                if isinstance(c, dict) and c.get("type") == "text"
                            ])
            return str(response)[:800]
        return str(response)[:800]


# =========================
# 4) 单例/入口
# =========================

_multi_agent_study_planner = None

def get_study_planner_agent() -> MultiAgentStudyPlanner:
    global _multi_agent_study_planner
    if _multi_agent_study_planner is None:
        _multi_agent_study_planner = MultiAgentStudyPlanner()
    return _multi_agent_study_planner


async def main():
    planner = MultiAgentStudyPlanner()
    await planner.initialize()

    request = StudyRequest(
        learner_name="小明",
        subject="Python 数据分析",
        goal="能独立完成一个带可视化与简单建模的分析项目，并能读懂常见数据分析代码",
        current_level="学过Python基础语法，会写简单脚本，但pandas/numpy不熟",
        deadline="2026-03-15",
        study_days=14,
        daily_time_minutes=90,
        preferences=["项目驱动", "少而精的文章/文档", "配套练习"],
        constraints=["工作日只能晚上学习", "不想看超过30分钟的长视频"],
        free_text_input="希望每天都有可交付的小输出；最后做一个完整小项目"
    )

    plan = await planner.plan_study(request)
    print("✅ 生成的学习规划（JSON）:")
    print(plan.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
