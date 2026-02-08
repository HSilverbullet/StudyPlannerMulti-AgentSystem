from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .study_planner_agent import get_study_planner_agent
from .schemas import StudyRequest, StudyPlanResponse
import uvicorn

app = FastAPI(
    title="AI 学习规划助手",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

planner = get_study_planner_agent()

@app.post("/api/v1/study/plan", response_model=StudyPlanResponse)
async def plan_learning(request: StudyRequest):
    try:
        await planner.initialize()
        plan = await planner.plan_study(request)
        return StudyPlanResponse(success=True, message="规划成功", data=plan)
    except Exception as e:
        return StudyPlanResponse(success=False, message=str(e))
    
@app.get("/")
async def root():
    return {"message": "AI学习规划系统已启动！前端地址：http://127.0.0.1:5500"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)