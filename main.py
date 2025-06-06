from create_resume_docx import generate_docx_from_json
from usage import estimate_tokens_and_price
import json
import shutil
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Paths
ROOT = Path(__file__).parent
DATA = ROOT / "data"
PROMPTS = ROOT / "prompts"
RESUMES = ROOT / "resumes"
RESULTS = ROOT / "results"

# Input files
JD_FILE = DATA / "job_description.txt"
RESUME_FILE = DATA / "resume.txt"
HEADER_FILE = DATA / "header_data.json"

# Prompt templates
SYS_P = PROMPTS / "system"
USR_P = PROMPTS / "user"
STEP1_SYS = SYS_P / "step1_jd_analysis.md"
STEP2_SYS = SYS_P / "step2_keyword_mapping.md"
STEP3_SYS = SYS_P / "step3_generating_points.md"
STEP4_SYS = SYS_P / "step4_quantifying_metrics.md"
STEP5_SYS = SYS_P / "step5_remove_filler_words.md"
STEP6_SYS = SYS_P / "step6_resume_refinement.md"
STEP7_SYS = SYS_P / "step7_convert_to_json.md"

STEP1_USR = USR_P / "step1_user.md"
STEP2_USR = USR_P / "step2_user.md"
STEP3_USR = USR_P / "step3_user.md"
STEP4_USR = USR_P / "step4_user.md"
STEP5_USR = USR_P / "step5_user.md"
STEP6_USR = USR_P / "step6_user.md"
STEP7_USR = USR_P / "step7_user.md"

client = None  # Initialized after loading env vars

# Helpers
def load_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")

def call_openai(messages: list, purpose: str) -> str:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.3
        )
        content = resp.choices[0].message.content.strip()
        return content
    except Exception as e:
        raise RuntimeError(f"[{purpose}] OpenAI call failed: {e}")

# Pipeline steps (with token counting)
def extract_keywords(metrics: dict) -> str:
    jd_text = load_text(JD_FILE)
    sys_template = load_text(STEP1_SYS)
    user_template = load_text(STEP1_USR).replace("<JOB_DESCRIPTION>", jd_text)

    # Count input tokens for step 1
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    metrics["step1_in_tokens"] = tokens_in
    metrics["step1_in_cost"] = cost_in

    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "extract_keywords",
    )

    # Count output tokens for step 1
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    metrics["step1_out_tokens"] = tokens_out
    metrics["step1_out_cost"] = cost_out

    print("Completed Stage 1: extract_keywords")
    return response

def plan_keywords(metrics: dict, keywords: str) -> str:
    resume_text = load_text(RESUME_FILE)
    sys_template = load_text(STEP2_SYS)
    user_template = load_text(STEP2_USR).replace("<RESUME>", resume_text).replace("<RANKED_KEYWORDS>", keywords)

    # Count input tokens for step 2
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    metrics["step2_in_tokens"] = tokens_in
    metrics["step2_in_cost"] = cost_in

    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "plan_keywords",
    )

    # Count output tokens for step 2
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    metrics["step2_out_tokens"] = tokens_out
    metrics["step2_out_cost"] = cost_out

    print("Completed Stage 2: plan_keywords")
    return response

def apply_tailoring(metrics: dict, plan: str) -> str:
    resume_text = load_text(RESUME_FILE)
    sys_template = load_text(STEP3_SYS)
    user_template = load_text(STEP3_USR).replace("<INTEGRATION_PLAN>", plan).replace("<RESUME>", resume_text)

    # Count input tokens for step 3
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    metrics["step3_in_tokens"] = tokens_in
    metrics["step3_in_cost"] = cost_in

    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "apply_tailoring",
    )

    # Count output tokens for step 3
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    metrics["step3_out_tokens"] = tokens_out
    metrics["step3_out_cost"] = cost_out

    print("Completed Stage 3: apply_tailoring")
    return response

def quantify_metrics(metrics: dict, draft: str) -> str:
    sys_template = load_text(STEP4_SYS)
    user_template = load_text(STEP4_USR).replace("<TAILORED_RESUME>", draft)

    # Count input tokens for step 4
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    metrics["step4_in_tokens"] = tokens_in
    metrics["step4_in_cost"] = cost_in

    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "quantify_metrics",
    )

    # Count output tokens for step 4
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    metrics["step4_out_tokens"] = tokens_out
    metrics["step4_out_cost"] = cost_out

    print("Completed Stage 4: quantify_metrics")
    return response

def remove_fillers(metrics: dict, draft: str) -> str:
    sys_template = load_text(STEP5_SYS)
    user_template = load_text(STEP5_USR).replace("<TAILORED_RESUME>", draft)

    # Count input tokens for step 5
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    metrics["step5_in_tokens"] = tokens_in
    metrics["step5_in_cost"] = cost_in

    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "remove_fillers",
    )

    # Count output tokens for step 5
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    metrics["step5_out_tokens"] = tokens_out
    metrics["step5_out_cost"] = cost_out

    print("Completed Stage 5: remove_fillers")
    return response

def refine_resume(metrics: dict, draft: str) -> str:
    sys_template = load_text(STEP6_SYS)
    user_template = load_text(STEP6_USR).replace("<TAILORED_RESUME>", draft)

    # Count input tokens for step 6
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    metrics["step6_in_tokens"] = tokens_in
    metrics["step6_in_cost"] = cost_in

    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "refine_resume",
    )

    # Count output tokens for step 6
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    metrics["step6_out_tokens"] = tokens_out
    metrics["step6_out_cost"] = cost_out

    print("Completed Stage 6: refine_resume")
    return response

def convert_to_json(metrics: dict, resume_md: str) -> dict:
    sys_template = load_text(STEP7_SYS)
    user_template = load_text(STEP7_USR).replace("<TAILORED_RESUME>", resume_md)

    # Count input tokens for step 7
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    metrics["step7_in_tokens"] = tokens_in
    metrics["step7_in_cost"] = cost_in

    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "convert_to_json",
    )

    # Count output tokens for step 7
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    metrics["step7_out_tokens"] = tokens_out
    metrics["step7_out_cost"] = cost_out

    # Clean up JSON fences if present
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("''") and cleaned.endswith("''")):
        cleaned = cleaned.strip('"')

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON parse failed: {e}\nRaw: {response}")

    print("Completed Stage 7: convert_to_json")
    return result

# DOCX generation
def generate_docs(full_resume: dict, company: str, position: str, job_id: str):
    def sanitize(name: str) -> str:
        return "_".join(name.split()).replace("/", "_")

    comp = sanitize(company)
    pos = sanitize(position)
    jid = sanitize(job_id) if job_id else ""
    filename = f"{comp}_{pos}_{jid}.docx" if jid else f"{comp}_{pos}.docx"
    output1 = RESUMES / filename
    generate_docx_from_json(full_resume, output_path=str(output1))

    # Copy to Downloads
    dl = Path.home() / "Downloads"
    dl.mkdir(exist_ok=True)
    generate_docx_from_json(full_resume, output_path=str(dl / "praneeth_ravuri_resume.docx"))

    print(f"Generated DOCX at: {output1}")

# Full pipeline
def run_pipeline(company: str, position: str, job_id: str):
    metrics = {}
    totals = {
        "in_tokens": 0,
        "out_tokens": 0,
        "in_cost": 0.0,
        "out_cost": 0.0,
    }

    # Cleanup and ensure directories
    if RESULTS.exists():
        shutil.rmtree(RESULTS)
    RESULTS.mkdir(exist_ok=True)

    # Stage 1: extract keywords
    keywords = extract_keywords(metrics)
    totals["in_tokens"] += metrics["step1_in_tokens"]
    totals["in_cost"] += metrics["step1_in_cost"]
    totals["out_tokens"] += metrics["step1_out_tokens"]
    totals["out_cost"] += metrics["step1_out_cost"]

    # Stage 2: generate integration plan
    plan = plan_keywords(metrics, keywords)
    totals["in_tokens"] += metrics["step2_in_tokens"]
    totals["in_cost"] += metrics["step2_in_cost"]
    totals["out_tokens"] += metrics["step2_out_tokens"]
    totals["out_cost"] += metrics["step2_out_cost"]

    # Stage 3: apply tailoring
    draft1 = apply_tailoring(metrics, plan)
    totals["in_tokens"] += metrics["step3_in_tokens"]
    totals["in_cost"] += metrics["step3_in_cost"]
    totals["out_tokens"] += metrics["step3_out_tokens"]
    totals["out_cost"] += metrics["step3_out_cost"]

    # Stage 4: quantify metrics
    draft2 = quantify_metrics(metrics, draft1)
    totals["in_tokens"] += metrics["step4_in_tokens"]
    totals["in_cost"] += metrics["step4_in_cost"]
    totals["out_tokens"] += metrics["step4_out_tokens"]
    totals["out_cost"] += metrics["step4_out_cost"]

    # Stage 5: remove fillers
    draft3 = remove_fillers(metrics, draft2)
    totals["in_tokens"] += metrics["step5_in_tokens"]
    totals["in_cost"] += metrics["step5_in_cost"]
    totals["out_tokens"] += metrics["step5_out_tokens"]
    totals["out_cost"] += metrics["step5_out_cost"]

    # Stage 6: refine resume
    refined_md = refine_resume(metrics, draft3)
    totals["in_tokens"] += metrics["step6_in_tokens"]
    totals["in_cost"] += metrics["step6_in_cost"]
    totals["out_tokens"] += metrics["step6_out_tokens"]
    totals["out_cost"] += metrics["step6_out_cost"]

    # Stage 7: convert to JSON (body only)
    body_json = convert_to_json(metrics, refined_md)
    totals["in_tokens"] += metrics["step7_in_tokens"]
    totals["in_cost"] += metrics["step7_in_cost"]
    totals["out_tokens"] += metrics["step7_out_tokens"]
    totals["out_cost"] += metrics["step7_out_cost"]

    # Load header and merge
    header_json = json.loads(load_text(HEADER_FILE))
    full_json = {
        "header": header_json,
        **body_json
    }

    # Write final JSON
    final_json_path = RESULTS / "final_resume.json"
    final_json_path.write_text(json.dumps(full_json, indent=2), encoding="utf-8")

    # Generate DOCX files using merged JSON
    generate_docs(full_json, company, position, job_id)

    # Create a combined report with token metrics
    report_path = RESULTS / "report.md"
    with report_path.open("w", encoding="utf-8") as report:
        report.write(f"# Step 1: Keywords\n\n{keywords}\n\n")
        report.write(f"# Step 2: Plan\n\n{plan}\n\n")
        report.write(f"# Step 3: Draft\n\n{draft1}\n\n")
        report.write(f"# Step 4: Quantified\n\n{draft2}\n\n")
        report.write(f"# Step 5: Cleaned\n\n{draft3}\n\n")
        report.write(f"# Step 6: Refined\n\n{refined_md}\n\n")

        # Token usage summary
        report.write("## Token Usage and Costs\n\n")
        for step in range(1, 8):
            in_t = metrics[f"step{step}_in_tokens"]
            out_t = metrics[f"step{step}_out_tokens"]
            in_c = metrics[f"step{step}_in_cost"]
            out_c = metrics[f"step{step}_out_cost"]
            report.write(f"- Step {step} Input: {in_t} tokens, ${in_c:.6f}\n")
            report.write(f"- Step {step} Output: {out_t} tokens, ${out_c:.6f}\n\n")

        total_cost = totals["in_cost"] + totals["out_cost"]
        report.write(f"**Total Input Tokens:** {totals['in_tokens']}  \n")
        report.write(f"**Total Output Tokens:** {totals['out_tokens']}  \n")
        report.write(f"**Total Cost:** ${total_cost:.6f}\n")

    print(f"Pipeline completed successfully. Total cost: ${total_cost:.6f}")

if __name__ == "__main__":
    load_dotenv()
    client = OpenAI()
    company = input("Company Name: ").strip()
    position = input("Position: ").strip()
    job_id = input("Job ID (optional): ").strip()
    try:
        run_pipeline(company, position, job_id)
    except Exception as e:
        raise RuntimeError(f"Pipeline failed: {e}") from e
        