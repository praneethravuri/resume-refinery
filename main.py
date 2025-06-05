# main.py

import logging
from logging.handlers import RotatingFileHandler
import math
import json
import os
import shutil
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

from create_resume_docx import generate_docx_from_json as create_docx_from_json

# --------------------------------------------------
# 1) Logging Configuration: write to logs/resume_tailoring.log
# --------------------------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

log_path = LOG_DIR / "resume_tailoring.log"
if log_path.exists():
    log_path.unlink()  # Delete previous log file on each run

file_handler = RotatingFileHandler(
    filename=log_path,
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3
)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)

# Also print WARNING+ messages to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# --------------------------------------------------
# 2) Configuration of folder paths
# --------------------------------------------------
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
PROMPTS_DIR = ROOT_DIR / "prompts"
RESUMES_DIR = ROOT_DIR / "resumes"
RESULTS_DIR = ROOT_DIR / "results"

# Ensure necessary directories exist
DATA_DIR.mkdir(exist_ok=True)
PROMPTS_DIR.mkdir(exist_ok=True)
RESUMES_DIR.mkdir(exist_ok=True)

# File paths that will be cleared / recreated
JD_PATH = DATA_DIR / "job_description.txt"
RESUME_PATH = DATA_DIR / "resume.txt"

TAILORED_RESUME_PATH = RESULTS_DIR / "tailored_resume.md"
REPORT_PATH = RESULTS_DIR / "report.md"
FINAL_RESUME_JSON_PATH = RESULTS_DIR / "final_resume.json"
SIMILARITY_PATH = RESULTS_DIR / "similarity_score.md"

# Prompt files
STEP1_SYSTEM_PROMPT = PROMPTS_DIR / "system" / "extract_keywords.md"
STEP2_SYSTEM_PROMPT = PROMPTS_DIR / "system" / "plan_keywords.md"
TAILORING_PROMPT     = PROMPTS_DIR / "system" / "tailoring.md"
STEP4_SYSTEM_PROMPT  = PROMPTS_DIR / "system" / "update_skills.md"

STEP1_USER_PROMPT    = PROMPTS_DIR / "user" / "step1_user.md"
STEP2_USER_PROMPT    = PROMPTS_DIR / "user" / "step2_user.md"
STEP3_USER_PROMPT    = PROMPTS_DIR / "user" / "step3_user.md"
STEP4_USER_PROMPT    = PROMPTS_DIR / "user" / "step4_user.md"
CONVERT_USER_PROMPT  = PROMPTS_DIR / "user" / "convert_user.md"

# Header data path
HEADER_DATA_PATH = DATA_DIR / "header_data.json"

# --------------------------------------------------
# 3) Helper: call OpenAI with logging and retries
# --------------------------------------------------
def call_openai_with_logging(messages, purpose, model="gpt-4o", temperature=0.3, max_tokens=4000):
    """
    Wraps an OpenAI Chat call, logs inputs/outputs, and returns the assistant's content.
    """
    logger.debug(f"[{purpose}] Sending {len(messages)} messages to OpenAI (model={model}, temp={temperature}).")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        result = response.choices[0].message.content.strip()
        logger.debug(f"[{purpose}] Received response:\n{result[:200]}{'...' if len(result) > 200 else ''}")
        return result
    except Exception as e:
        logger.error(f"[{purpose}] Error calling OpenAI: {e}", exc_info=True)
        raise

# --------------------------------------------------
# 4) Helper: read text from a file
# --------------------------------------------------
def read_text_file(path: Path) -> str:
    if not path.exists():
        logger.error(f"Missing required file: {path}")
        raise FileNotFoundError(f"File not found: {path}")
    text = path.read_text(encoding="utf-8")
    logger.debug(f"Read {len(text)} characters from {path}.")
    return text

# --------------------------------------------------
# 5) Helper: compute cosine similarity of two embeddings
# --------------------------------------------------
def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)

# --------------------------------------------------
# 6) Step 1: Extract & rank keywords from JD
# --------------------------------------------------
def analyze_jd() -> str:
    job_description = read_text_file(JD_PATH)
    step1_system = read_text_file(STEP1_SYSTEM_PROMPT)
    step1_user_tpl = read_text_file(STEP1_USER_PROMPT)
    step1_user = step1_user_tpl.replace("<JOB_DESCRIPTION>", job_description)

    ranked_keywords = call_openai_with_logging(
        [
            {"role": "system", "content": step1_system},
            {"role": "user",   "content": step1_user  }
        ],
        purpose="step1_extract_keywords"
    )
    logger.info("Step 1 completed: ranked keywords obtained.")
    return ranked_keywords

# --------------------------------------------------
# 7) Step 2: Plan keyword insertion into resume
# --------------------------------------------------
def keyword_insertion_plan(ranked_keywords: str) -> str:
    resume_text = read_text_file(RESUME_PATH)
    step2_system = read_text_file(STEP2_SYSTEM_PROMPT)
    step2_user_tpl = read_text_file(STEP2_USER_PROMPT)

    step2_user = (
        step2_user_tpl
        .replace("<RESUME>", resume_text)
        .replace("<RANKED_KEYWORDS>", ranked_keywords)
    )
    tailoring_plan = call_openai_with_logging(
        [
            {"role": "system", "content": step2_system},
            {"role": "user",   "content": step2_user   }
        ],
        purpose="step2_plan_keywords"
    )
    logger.info("Step 2 completed: tailoring plan obtained.")
    return tailoring_plan

# --------------------------------------------------
# 8) Step 3: Apply tailoring plan (intermediate)
# --------------------------------------------------
def apply_tailoring_plan(tailoring_plan: str) -> str:
    resume_text = read_text_file(RESUME_PATH)
    step3_user_tpl = read_text_file(STEP3_USER_PROMPT)
    step3_user = (
        step3_user_tpl
        .replace("<RESUME>", resume_text)
        .replace("<TAILORING_PLAN>", tailoring_plan)
    )
    tailored_resume_mid = call_openai_with_logging(
        [
            {"role": "system", "content": read_text_file(TAILORING_PROMPT)},
            {"role": "user",   "content": step3_user               }
        ],
        purpose="step3_apply_tailoring"
    )
    logger.info("Step 3 completed: intermediate tailored resume obtained.")
    return tailored_resume_mid

# --------------------------------------------------
# 9) Step 4: Update skills section in tailored resume
# --------------------------------------------------
def update_skills_section(tailored_resume_mid: str) -> str:
    step4_system = read_text_file(STEP4_SYSTEM_PROMPT)
    step4_user_tpl = read_text_file(STEP4_USER_PROMPT)
    step4_user = step4_user_tpl.replace("<TAILORED_RESUME>", tailored_resume_mid)

    final_resume = call_openai_with_logging(
        [
            {"role": "system", "content": step4_system},
            {"role": "user",   "content": step4_user  }
        ],
        purpose="step4_update_skills"
    )
    logger.info("Step 4 completed: final tailored resume obtained.")
    return final_resume

# --------------------------------------------------
# 10) Step 5: Compute similarity score & generate report
# --------------------------------------------------
def compute_similarity_score(final_resume: str) -> float:
    job_description = read_text_file(JD_PATH)
    logger.info("Computing embedding for Job Description...")
    jd_embed = client.embeddings.create(
        model="text-embedding-ada-002", input=job_description
    ).data[0].embedding

    logger.info("Computing embedding for Final Tailored Resume...")
    resume_embed = client.embeddings.create(
        model="text-embedding-ada-002", input=final_resume
    ).data[0].embedding

    score = cosine_similarity(jd_embed, resume_embed)
    logger.debug(f"Similarity score: {score:.4f}")
    return score

def create_report(ranked_keywords: str, tailoring_plan: str, final_resume: str, similarity_score: float) -> None:
    """
    Combine Steps 1, 2, 4, and the similarity score into one Markdown report.
    """
    similarity_pct = round(similarity_score * 100, 2)
    report_lines = [
        "# Step 1: Ranked Keywords\n\n",
        ranked_keywords + "\n\n",
        "# Step 2: Tailoring Plan\n\n",
        tailoring_plan + "\n\n",
        "# Step 4: Final Tailored Resume\n\n",
        final_resume + "\n\n",
        "# Step 5: Similarity Score\n\n",
        f"Cosine similarity (JD ↔ Tailored Resume): {similarity_score:.4f} (~{similarity_pct}%)\n"
    ]
    REPORT_PATH.write_text("".join(report_lines), encoding="utf-8")
    logger.info(f"Report written to {REPORT_PATH}.")

# --------------------------------------------------
# 11) Step 6: Convert final resume to JSON
# --------------------------------------------------
def convert_resume_to_json(final_resume: str) -> None:
    convert_user_tpl = read_text_file(CONVERT_USER_PROMPT)
    convert_user = convert_user_tpl.replace("<FINAL_TAILORED_RESUME>", final_resume)

    resume_body_json_text = call_openai_with_logging(
        [
            {"role": "system", "content": "You are a strict JSON‐only assistant. Output exactly one JSON blob."},
            {"role": "user",   "content": convert_user                               }
        ],
        purpose="step6_convert_to_json"
    )

    # Strip away any Markdown fences or quote wrappers
    cleaned = resume_body_json_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    if cleaned.startswith('"""') and cleaned.endswith('"""'):
        cleaned = cleaned[3:-3].strip()
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]

    try:
        resume_body = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON for resume conversion: %s\nRaw output:\n%s",
            e,
            resume_body_json_text,
        )
        raise

    if not HEADER_DATA_PATH.exists():
        logger.error(f"Header data file not found: {HEADER_DATA_PATH}")
        raise FileNotFoundError(f"File not found: {HEADER_DATA_PATH}")
    HEADER_DATA = json.loads(HEADER_DATA_PATH.read_text(encoding="utf-8"))
    
    full_resume_json = {"header": HEADER_DATA, **resume_body}
    FINAL_RESUME_JSON_PATH.write_text(json.dumps(full_resume_json, indent=2), encoding="utf-8")
    logger.info(f"JSON resume written to {FINAL_RESUME_JSON_PATH}.")

# --------------------------------------------------
# 12) Step 7: Generate DOCX copies
# --------------------------------------------------
def generate_docx_files(company: str, position: str, jobid: str) -> None:
    """
    Create two DOCX files:
      1. Named {company}_{position}_{jobid}.docx under resumes/
      2. Fixed name 'praneeth_ravuri_resume.docx' in the user's Downloads folder
    """
    # Load JSON résumé from disk
    resume_json_data = json.loads(FINAL_RESUME_JSON_PATH.read_text(encoding="utf-8"))

    def _sanitize(text: str) -> str:
        return "_".join(text.strip().split()).replace("/", "_")

    company_clean  = _sanitize(company)
    position_clean = _sanitize(position)
    jobid_clean    = _sanitize(jobid) if jobid.strip() else ""

    if jobid_clean:
        filename1 = f"{company_clean}_{position_clean}_{jobid_clean}.docx"
    else:
        filename1 = f"{company_clean}_{position_clean}.docx"

    # 1st copy: saved under resumes/
    output_path1 = RESUMES_DIR / filename1
    create_docx_from_json(resume_json_data, output_path=str(output_path1))
    logger.info(f"Generated DOCX: {output_path1}")

    # 2nd copy: saved in Downloads folder
    downloads_dir = Path.home() / "Downloads"
    downloads_dir.mkdir(exist_ok=True)
    output_path2 = downloads_dir / "praneeth_ravuri_resume.docx"
    create_docx_from_json(resume_json_data, output_path=str(output_path2))
    logger.info(f"Generated DOCX copy in Downloads: {output_path2}")

# --------------------------------------------------
# 13) Full pipeline orchestration
# --------------------------------------------------
def run_pipeline(company: str, position: str, jobid: str):
    # --- Pre-cleanup: clear results/ and job_description.txt ---
    if RESULTS_DIR.exists():
        shutil.rmtree(RESULTS_DIR)
    RESULTS_DIR.mkdir(exist_ok=True)

    # Step 1: Extract & rank keywords
    ranked_keywords = analyze_jd()

    # Step 2: Plan keyword insertion
    tailoring_plan = keyword_insertion_plan(ranked_keywords)

    # Step 3: Apply tailoring plan
    tailored_resume_mid = apply_tailoring_plan(tailoring_plan)

    # Step 4: Update skills section
    final_resume = update_skills_section(tailored_resume_mid)

    # Write final resume Markdown to results/
    TAILORED_RESUME_PATH.write_text(final_resume, encoding="utf-8")
    logger.info(f"Final tailored resume written to {TAILORED_RESUME_PATH}")

    # Step 5: Compute similarity and create report
    similarity_score = compute_similarity_score(final_resume)
    create_report(ranked_keywords, tailoring_plan, final_resume, similarity_score)

    # Step 6: Convert to JSON
    convert_resume_to_json(final_resume)

    # Step 7: Generate DOCX files
    generate_docx_files(company, position, jobid)

    # Finally, clear job_description.txt again
    if JD_PATH.exists():
        JD_PATH.write_text("", encoding="utf-8")

    print("✅ All steps completed. See logs in 'logs/resume_tailoring.log' for details.")


if __name__ == "__main__":
    # Load environment variables (expects OPENAI_API_KEY set)
    load_dotenv()
    client = OpenAI()

    print("Please enter the following details for naming the resume files.")
    company = input("Company Name: ").strip()
    position = input("Position Name: ").strip()
    jobid = input("Job ID (optional; press Enter to skip): ").strip()

    try:
        run_pipeline(company, position, jobid)
    except Exception as e:
        logger.error("Pipeline terminated with an error: %s", e, exc_info=True)
        print(f"❌ Pipeline failed: {e}")
