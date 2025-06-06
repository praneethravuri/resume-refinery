from create_resume_docx import generate_docx_from_json
import logging
from logging.handlers import RotatingFileHandler
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

# Configure logging


def setup_logging():
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "resume_tailoring.log"
    if log_file.exists():
        log_file.unlink()
    handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s", "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(fmt)
    root.addHandler(console)
    return logging.getLogger(__name__)


logger = setup_logging()
client = None  # Initialized after loading env vars

# Helpers


def load_text(path: Path) -> str:
    if not path.exists():
        logger.error(f"Missing file: {path}")
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def call_openai(messages: list, purpose: str) -> str:
    logger.debug(f"[{purpose}] Sending {len(messages)} messages to OpenAI.")
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.3)
        content = resp.choices[0].message.content.strip()
        logger.debug(
            f"[{purpose}] Received response: {content[:200]}{'...' if len(content) > 200 else ''}")
        return content
    except Exception as e:
        logger.error(f"[{purpose}] OpenAI call failed: {e}", exc_info=True)
        raise

# Pipeline steps


def extract_keywords() -> str:
    jd_text = load_text(JD_FILE)
    sys_template = load_text(STEP1_SYS)
    user_template = load_text(STEP1_USR).replace("<JOB_DESCRIPTION>", jd_text)
    return call_openai([
        {"role": "system", "content": sys_template},
        {"role": "user",   "content": user_template}
    ], "extract_keywords")


def plan_keywords(keywords: str) -> str:
    resume_text = load_text(RESUME_FILE)
    sys_template = load_text(STEP2_SYS)
    user_template = load_text(STEP2_USR).replace(
        "<RESUME>", resume_text).replace("<RANKED_KEYWORDS>", keywords)
    return call_openai([
        {"role": "system", "content": sys_template},
        {"role": "user",   "content": user_template}
    ], "plan_keywords")


def apply_tailoring(plan: str) -> str:
    resume_text = load_text(RESUME_FILE)
    sys_template = load_text(STEP3_SYS)
    user_template = load_text(STEP3_USR).replace(
        "<INTEGRATION_PLAN>", plan).replace("<RESUME>", resume_text)
    return call_openai([
        {"role": "system", "content": sys_template},
        {"role": "user",   "content": user_template}
    ], "apply_tailoring")


def quantify_metrics(draft: str) -> str:
    sys_template = load_text(STEP4_SYS)
    user_template = load_text(STEP4_USR).replace("<TAILORED_RESUME>", draft)
    return call_openai([
        {"role": "system", "content": sys_template},
        {"role": "user",   "content": user_template}
    ], "quantify_metrics")


def remove_fillers(draft: str) -> str:
    sys_template = load_text(STEP5_SYS)
    user_template = load_text(STEP5_USR).replace("<TAILORED_RESUME>", draft)
    return call_openai([
        {"role": "system", "content": sys_template},
        {"role": "user",   "content": user_template}
    ], "remove_fillers")


def refine_resume(draft: str) -> str:
    sys_template = load_text(STEP6_SYS)
    user_template = load_text(STEP6_USR).replace("<TAILORED_RESUME>", draft)
    return call_openai([
        {"role": "system", "content": sys_template},
        {"role": "user",   "content": user_template}
    ], "refine_resume")


def convert_to_json(resume_md: str) -> dict:
    sys_template = load_text(STEP7_SYS)
    user_template = load_text(STEP7_USR).replace(
        "<TAILORED_RESUME>", resume_md)
    response = call_openai([
        {"role": "system", "content": sys_template},
        {"role": "user",   "content": user_template}
    ], "convert_to_json")
    cleaned = response.strip()
    # Remove markdown fences or extraneous quotes
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
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}\nRaw: {response}")
        raise


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
    generate_docx_from_json(full_resume, output_path=str(
        dl / "praneeth_ravuri_resume.docx"))
    logger.info(f"Generated DOCX: {output1}")

# Full pipeline


def run_pipeline(company: str, position: str, job_id: str):
    # Cleanup and ensure directories
    if RESULTS.exists():
        shutil.rmtree(RESULTS)
    RESULTS.mkdir(exist_ok=True)

    # Stage 1: extract keywords
    keywords = extract_keywords()
    # Stage 2: generate integration plan
    plan = plan_keywords(keywords)
    # Stage 3: apply tailoring
    draft1 = apply_tailoring(plan)
    # Stage 4: quantify metrics
    draft2 = quantify_metrics(draft1)
    # Stage 5: remove fillers
    draft3 = remove_fillers(draft2)
    # Stage 6: refine resume
    refined_md = refine_resume(draft3)
    # Stage 7: convert to JSON (body only)
    body_json = convert_to_json(refined_md)

    # Load header and merge
    header_json = json.loads(load_text(HEADER_FILE))
    full_json = {
        "header": header_json,
        **body_json
    }

    # Write final JSON
    final_json_path = RESULTS / "final_resume.json"
    final_json_path.write_text(json.dumps(
        full_json, indent=2), encoding="utf-8")

    # Generate DOCX files using merged JSON
    generate_docs(full_json, company, position, job_id)

    # Create a combined report
    report_path = RESULTS / "report.md"
    with report_path.open("w", encoding="utf-8") as report:
        report.write(f"# Step 1: Keywords\n\n{keywords}\n\n")
        report.write(f"# Step 2: Plan\n\n{plan}\n\n")
        report.write(f"# Step 3: Draft\n\n{draft1}\n\n")
        report.write(f"# Step 4: Quantified\n\n{draft2}\n\n")
        report.write(f"# Step 5: Cleaned\n\n{draft3}\n\n")
        report.write(f"# Step 6: Refined\n\n{refined_md}\n")

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    load_dotenv()
    client = OpenAI()
    company = input("Company Name: ").strip()
    position = input("Position: ").strip()
    job_id = input("Job ID (optional): ").strip()
    try:
        run_pipeline(company, position, job_id)
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        print(f"Error: {e}")
