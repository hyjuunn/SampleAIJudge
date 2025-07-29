from fastapi import FastAPI, Body
from pydantic import BaseModel
from lib.oracle_mvp_ai.ai_judge import AiJudge
from lib.oracle_mvp_ai.llm_clients.openai_client import OpenAIClient
import os
from fastapi.responses import JSONResponse
from fastapi import HTTPException
import glob
import json
import yaml
from fastapi import Request
import asyncio
from dotenv import load_dotenv
from bson import ObjectId
from fastapi import UploadFile, File, Form
from lib.oracle_mvp_ai import metrics

app = FastAPI()

# .env 파일을 프로젝트 루트에서 로드
load_dotenv()

# 환경변수에서 OPENAI_API_KEY를 읽어옴
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-...your-key...")
ai_judge = AiJudge(OPENAI_API_KEY)

class AskRequest(BaseModel):
    topic: str
    posts: list[str]
    prompt_metadata_filename: str
    type: str = "final"

@app.post("/ask")
def ask(request: AskRequest):
    result = ai_judge.ask_question(
        topic=request.topic,
        posts=request.posts,
        prompt_metadata_filename=request.prompt_metadata_filename,
        type=request.type
    )
    return {"result": result}

# 프롬프트 파일 리스트 조회
@app.get("/prompts")
def list_prompts():
    prompt_dir = os.path.join(os.path.dirname(__file__), '../lib/oracle_mvp_ai/prompt_metadata')
    files = [f for f in os.listdir(prompt_dir) if f.endswith('.yaml')]
    return {"prompts": files}

# 프롬프트 파일 내용 조회
@app.get("/prompts/{filename}")
def get_prompt(filename: str):
    prompt_dir = os.path.join(os.path.dirname(__file__), '../lib/oracle_mvp_ai/prompt_metadata')
    file_path = os.path.join(prompt_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Prompt file not found")
    with open(file_path, encoding='utf-8') as f:
        content = f.read()
    return {"content": content}

# 프롬프트 추가
@app.post("/prompts")
def add_prompt(filename: str = Form(...), content: str = Form(...)):
    print(filename, content)
    if not (filename.endswith('.yaml') or filename.endswith('.json')):
        raise HTTPException(status_code=400, detail="파일명은 .yaml 또는 .json으로 끝나야 합니다.")
    prompt_dir = os.path.join(os.path.dirname(__file__), '../lib/oracle_mvp_ai/prompt_metadata')
    file_path = os.path.join(prompt_dir, filename)
    print(file_path)
    if os.path.exists(file_path):
        raise HTTPException(status_code=409, detail="이미 존재하는 파일명입니다.")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {"success": True, "filename": filename}

# 데이터셋 버전/파일 리스트 조회
@app.get("/datasets")
def list_datasets():
    dataset_dir = os.path.join(os.path.dirname(__file__), '../dataset')
    result = []
    for version in sorted(os.listdir(dataset_dir)):
        version_path = os.path.join(dataset_dir, version)
        if os.path.isdir(version_path):
            files = [f for f in os.listdir(version_path) if f.endswith('.json')]
            result.append({"version": version, "files": files})
    return {"datasets": result}

# 데이터셋 파일 내용 조회
@app.get("/datasets/{version}/{filename}")
def get_dataset(version: str, filename: str):
    dataset_dir = os.path.join(os.path.dirname(__file__), f'../dataset/{version}')
    file_path = os.path.join(dataset_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")
    with open(file_path, encoding='utf-8') as f:
        content = json.load(f)
    return content

# 데이터셋 추가
@app.post("/datasets/{version}")
def add_dataset(version: str, filename: str = Form(...), content: str = Form(...)):
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="파일명은 .json으로 끝나야 합니다.")
    dataset_dir = os.path.join(os.path.dirname(__file__), f'../dataset/{version}')
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
    file_path = os.path.join(dataset_dir, filename)
    if os.path.exists(file_path):
        raise HTTPException(status_code=409, detail="이미 존재하는 파일명입니다.")
    # 스키마 검사: 같은 폴더 내 다른 파일과 키 구조 비교
    import json
    new_data = json.loads(content)
    for f in os.listdir(dataset_dir):
        if f.endswith('.json') and f != filename:
            with open(os.path.join(dataset_dir, f), encoding='utf-8') as ref:
                try:
                    ref_data = json.load(ref)
                    if isinstance(ref_data, list) and isinstance(new_data, list) and ref_data and new_data:
                        if set(ref_data[0].keys()) != set(new_data[0].keys()):
                            raise HTTPException(status_code=400, detail=f"스키마 불일치: {f}와(과) 다름")
                    elif isinstance(ref_data, dict) and isinstance(new_data, dict):
                        if set(ref_data.keys()) != set(new_data.keys()):
                            raise HTTPException(status_code=400, detail=f"스키마 불일치: {f}와(과) 다름")
                except Exception as e:
                    continue
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {"success": True, "filename": filename}

# 결과 파일 리스트 및 내용 조회 (결과는 playground/results/에 저장한다고 가정)
@app.get("/results")
def list_results():
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
    return {"results": files}

@app.get("/results/{filename}")
def get_result(filename: str):
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    file_path = os.path.join(results_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Result file not found")
    with open(file_path, encoding='utf-8') as f:
        content = json.load(f)
    return content

@app.post("/run_judge")
def run_judge(request: dict):
    """
    프롬프트 파일명(prompt_filename)과 데이터셋 버전/파일명(dataset_version, dataset_filename)을 받아 judge 실행 후 결과를 저장하고 반환
    result_file 파라미터가 있으면 해당 이름으로 결과를 저장한다.
    """
    prompt_filename = request.get('prompt_filename')
    dataset_version = request.get('dataset_version')
    dataset_filename = request.get('dataset_filename')
    result_file = request.get('result_file')

    # 파일 경로
    prompt_dir = os.path.join(os.path.dirname(__file__), '../lib/oracle_mvp_ai/prompt_metadata')
    dataset_dir = os.path.join(os.path.dirname(__file__), f'../dataset/{dataset_version}')
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    prompt_path = os.path.join(prompt_dir, prompt_filename)
    dataset_path = os.path.join(dataset_dir, dataset_filename)

    # 파일 존재 확인
    if not os.path.exists(prompt_path):
        raise HTTPException(status_code=404, detail="Prompt file not found")
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")

    # 데이터셋 로드 및 ObjectId 필드 감싸기
    def convert_oid_fields(obj):
        if isinstance(obj, dict):
            new_obj = {}
            for k, v in obj.items():
                if k in ['_id', 'id', 'user_id', 'topic_id']:
                    # ObjectId로 감싸기
                    new_obj[k] = ObjectId(v)
                else:
                    new_obj[k] = convert_oid_fields(v)
            return new_obj
        elif isinstance(obj, list):
            return [convert_oid_fields(item) for item in obj]
        else:
            return obj

    with open(dataset_path, encoding='utf-8') as f:
        dataset = json.load(f)
        dataset = convert_oid_fields(dataset)

    # judge 실행 (비동기)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(ai_judge.judge(dataset))
    loop.close()

    # 결과 저장 (사용자 지정 파일명 우선)
    if result_file and result_file.endswith('.json'):
        result_filename = result_file
    else:
        result_filename = f"{os.path.splitext(prompt_filename)[0]}_{dataset_version}_{os.path.splitext(dataset_filename)[0]}.json"
    result_path = os.path.join(results_dir, result_filename)

    # ObjectId를 문자열로 변환하는 함수
    def convert_objectid_to_str(obj):
        if isinstance(obj, dict):
            return {k: convert_objectid_to_str(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_objectid_to_str(item) for item in obj]
        elif isinstance(obj, ObjectId):
            return str(obj)
        else:
            return obj

    # 결과 내 ObjectId를 문자열로 변환
    result_for_json = convert_objectid_to_str(result)

    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result_for_json, f, ensure_ascii=False, indent=2)

    return {"result": result_for_json, "result_file": result_filename}

@app.post('/run_consistency')
async def run_consistency(request: Request):
    data = await request.json()
    prompt_filename = data['prompt_filename']
    dataset_version = data['dataset_version']
    dataset_filename = data['dataset_filename']
    result_file = data['result_file']
    n = int(data.get('n', 5))

    # 결과 저장 폴더 생성
    result_dir = os.path.join('playground', 'results', 'consistency')
    os.makedirs(result_dir, exist_ok=True)
    result_path = os.path.join(result_dir, result_file)

    # 데이터셋 로드 (run_judge와 동일하게)
    dataset_dir = os.path.join(os.path.dirname(__file__), f'../dataset/{dataset_version}')
    dataset_path = os.path.join(dataset_dir, dataset_filename)
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")
    with open(dataset_path, encoding='utf-8') as f:
        dataset = json.load(f)

    # N회 실행 결과 저장 (비동기 호출)
    results = []
    for i in range(n):
        result = await ai_judge.judge(dataset)
        results.append(result)

    # 지표 계산
    metrics_result = metrics.calculate_consistency_metrics(results)

    # 파일 저장
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump({
            'prompt_filename': prompt_filename,
            'dataset_version': dataset_version,
            'dataset_filename': dataset_filename,
            'n': n,
            'results': results,
            'metrics': metrics_result
        }, f, ensure_ascii=False, indent=2)

    return JSONResponse({
        'result_file': os.path.basename(result_path),
        'metrics': metrics_result
    })

@app.post('/recalc_consistency')
def recalc_consistency(request: dict):
    """
    결과 파일명을 받아서, 해당 파일의 원본 결과(results)로 지표만 다시 계산해서 반환
    """
    result_file = request.get('result_file')
    result_dir = os.path.join('playground', 'results', 'consistency')
    result_path = os.path.join(result_dir, result_file)
    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Result file not found")
    with open(result_path, encoding='utf-8') as f:
        data = json.load(f)
    results = data.get('results', [])
    metrics_result = metrics.calculate_consistency_metrics(results)
    return {"metrics": metrics_result}


