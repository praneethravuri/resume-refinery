# ========== main.py (Refactored with Cost Tracking) ==========
from create_resume_docx import generate_docx_from_json
from usage import estimate_tokens_and_price
import json
import shutil
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import sys

# Define file paths
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

# Output files
REPORT = RESULTS / "report.md"
TAILORED_RESUME = RESULTS / "tailored_resume.json"

# OpenAI client placeholder
client = None  # Will be initialized after loading environment variables

# Global accumulators for token & cost tracking
total_tokens_in = 0
total_cost_in = 0.0
total_tokens_out = 0
total_cost_out = 0.0

# --------- Helper Functions ---------

def load_text(path: Path) -> str:
    """
    Load text content from a given file path.

    Args:
        path (Path): Path to the text file.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If reading the file fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Error reading file {path}: {e}")


def call_openai(messages: list, purpose: str) -> str:
    """
    Call the OpenAI ChatCompletion API with the given messages.

    Args:
        messages (list): List of message dicts for the API.
        purpose (str): A label for error context.

    Returns:
        str: The content of the API response.

    Raises:
        RuntimeError: If the API call fails.
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=messages, temperature=0.3
        )
        content = resp.choices[0].message.content.strip()
        return content
    except Exception as e:
        raise RuntimeError(f"[{purpose}] OpenAI call failed: {e}")
    
def write_to_report(response: str):
    """
    Write the response content to the report file.

    Args:
        response (str): The content to write to the report.
    """
    try:
        with REPORT.open("a", encoding="utf-8") as report_file:
            report_file.write(response + "\n\n")
    except Exception as e:
        raise RuntimeError(f"Error writing to report: {e}")

def print_metrics(tokens_in: int, cost_in: float, tokens_out: int, cost_out: float):
    """
    Print token usage and cost for a stage.
    """
    print(f"Input Tokens: {tokens_in}, Cost: ${cost_in:.6f}")
    print(f"Output Tokens: {tokens_out}, Cost: ${cost_out:.6f}\n")

# --------- Pipeline Steps ---------

def extract_keywords() -> str:
    """
    Stage 1: Extract prioritized keywords from the job description.
    Updates global accumulators with token usage and cost.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    jd_text = load_text(JD_FILE)
    sys_template = load_text(STEP1_SYS)
    user_template = load_text(STEP1_USR).replace("<JOB_DESCRIPTION>", jd_text)

    # Count input tokens and cost for Stage 1
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    total_tokens_in += tokens_in
    total_cost_in += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "extract_keywords",
    )

    # Count output tokens and cost for Stage 1
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out += cost_out

    # Print summary for Stage 1
    print("\nStage 1 Complete: Keywords extracted.")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("## Stage 1: Extract Keywords\n" + response)

    return response


def plan_keywords(keywords: str) -> str:
    """
    Stage 2: Generate integration plan mapping keywords to resume.
    Updates global accumulators with token usage and cost.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    resume_text = load_text(RESUME_FILE)
    sys_template = load_text(STEP2_SYS)
    user_template = (
        load_text(STEP2_USR)
        .replace("<RESUME>", resume_text)
        .replace("<RANKED_KEYWORDS>", keywords)
    )

    # Count input tokens and cost for Stage 2
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    total_tokens_in += tokens_in
    total_cost_in += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "plan_keywords",
    )

    # Count output tokens and cost for Stage 2
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out += cost_out

    # Print summary for Stage 2
    print("\nStage 2 Complete: Integration plan generated.")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("## Stage 2: Keyword Integration Plan\n" + response)

    return response


def apply_tailoring(plan: str) -> str:
    """
    Stage 3: Apply the integration plan to the resume.
    Updates global accumulators with token usage and cost.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    resume_text = load_text(RESUME_FILE)
    sys_template = load_text(STEP3_SYS)
    user_template = (
        load_text(STEP3_USR)
        .replace("<INTEGRATION_PLAN>", plan)
        .replace("<RESUME>", resume_text)
    )

    # Count input tokens and cost for Stage 3
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    total_tokens_in += tokens_in
    total_cost_in += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "apply_tailoring",
    )

    # Count output tokens and cost for Stage 3
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out += cost_out

    # Print summary for Stage 3
    print("\nStage 3 Complete: Tailored resume draft generated.")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("## Stage 3: Tailored Resume Draft\n" + response)

    return response


def quantify_metrics(draft: str) -> str:
    """
    Stage 4: Ensure every bullet has quantifiable metrics.
    Updates global accumulators with token usage and cost.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    sys_template = load_text(STEP4_SYS)
    user_template = load_text(STEP4_USR).replace("<TAILORED_RESUME>", draft)

    # Count input tokens and cost for Stage 4
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    total_tokens_in += tokens_in
    total_cost_in += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "quantify_metrics",
    )

    # Count output tokens and cost for Stage 4
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out += cost_out

    # Print summary for Stage 4
    print("\nStage 4 Complete: Metrics quantified.")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("## Stage 4: Quantified Metrics\n" + response)

    return response


def remove_fillers(draft: str) -> str:
    """
    Stage 5: Remove filler words, buzzwords, and jargon.
    Updates global accumulators with token usage and cost.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    sys_template = load_text(STEP5_SYS)
    user_template = load_text(STEP5_USR).replace("<TAILORED_RESUME>", draft)

    # Count input tokens and cost for Stage 5
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    total_tokens_in += tokens_in
    total_cost_in += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "remove_fillers",
    )

    # Count output tokens and cost for Stage 5
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out += cost_out

    # Print summary for Stage 5
    print("\nStage 5 Complete: Fillers removed.")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("## Stage 5: Remove Fillers\n" + response)

    return response


def refine_resume(draft: str) -> str:
    """
    Stage 6: Refine resume to final, domain-aligned format.
    Updates global accumulators with token usage and cost.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    sys_template = load_text(STEP6_SYS)
    user_template = load_text(STEP6_USR).replace("<TAILORED_RESUME>", draft)

    # Count input tokens and cost for Stage 6
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    total_tokens_in += tokens_in
    total_cost_in += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "refine_resume",
    )

    # Count output tokens and cost for Stage 6
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out += cost_out

    # Print summary for Stage 6
    print("\nStage 6 Complete: Resume refined.")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("## Stage 6: Refine Resume\n" + response)

    return response


def convert_to_json(resume_md: str) -> dict:
    """
    Stage 7: Convert final markdown resume to JSON structure.
    Updates global accumulators with token usage and cost.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    sys_template = load_text(STEP7_SYS)
    user_template = load_text(STEP7_USR).replace("<TAILORED_RESUME>", resume_md)

    # Count input tokens and cost for Stage 7
    tokens_in, cost_in = estimate_tokens_and_price(sys_template + user_template, "input")
    total_tokens_in += tokens_in
    total_cost_in += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_template},
            {"role": "user", "content": user_template},
        ],
        "convert_to_json",
    )

    # Count output tokens and cost for Stage 7
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out += cost_out

    # Clean JSON fences if present
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

    # Print summary for Stage 7
    print("\nStage 7 Complete: JSON conversion done.")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("## Stage 7: Convert to JSON\n" + response)

    return result

# --------- DOCX Generation ---------

def generate_docs(full_resume: dict, company: str, position: str, job_id: str):
    """
    Generate DOCX files for the final resume and copy to Downloads.
    """
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

    print(f"Generated DOCX at: {output1}\n")

# --------- Full Pipeline ---------

def run_pipeline(company: str, position: str, job_id: str):
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    # Ensure results directory is clean
    try:
        if RESULTS.exists():
            shutil.rmtree(RESULTS)
        RESULTS.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Error preparing results directory: {e}")
        sys.exit(1)

    # Stage executions with error handling
    try:
        keywords = extract_keywords()
        plan = plan_keywords(keywords)
        draft1 = apply_tailoring(plan)
        draft2 = quantify_metrics(draft1)
        draft3 = remove_fillers(draft2)
        refined_md = refine_resume(draft3)
        body_json = convert_to_json(refined_md)
    except Exception as e:
        print(f"Pipeline failed during execution: {e}")
        sys.exit(1)

    # Merge header JSON and final resume
    try:
        header_json = json.loads(load_text(HEADER_FILE))
        full_json = {"header": header_json, **body_json}

        # Write final JSON
        final_json_path = TAILORED_RESUME
        final_json_path.write_text(json.dumps(full_json, indent=2), encoding="utf-8")

        # Append total cost summary to report
        cost_summary = (
            "## Total Token Usage & Cost Summary\n"
            f"- Total Input Tokens: {total_tokens_in}, Total Input Cost: ${total_cost_in:.6f}\n"
            f"- Total Output Tokens: {total_tokens_out}, Total Output Cost: ${total_cost_out:.6f}\n"
        )
        write_to_report(cost_summary)

    except Exception as e:
        print(f"Error generating final JSON: {e}")
        sys.exit(1)

    # Generate DOCX files
    generate_docs(full_json, company, position, job_id)

# --------- Entry Point ---------

if __name__ == "__main__":
    load_dotenv()
    try:
        client = OpenAI()
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        sys.exit(1)

    company = input("Company Name: ").strip()
    position = input("Position: ").strip()
    job_id = input("Job ID (optional): ").strip()

    if not company or not position:
        print("Company and Position are required.")
        sys.exit(1)

    run_pipeline(company, position, job_id)
