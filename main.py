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

# New Prompt templates for two stages
JD_SYS      = PROMPTS / "system" / "jd_analysis_prompt.md"
JD_USER     = PROMPTS / "user"   / "jd_analysis_user.md"
RT_SYS      = PROMPTS / "system" / "resume_tailoring_prompt.md"
RT_USER     = PROMPTS / "user"   / "resume_tailoring_user.md"

# Output files
REPORT         = RESULTS / "report.md"
TAILORED_JSON  = RESULTS / "tailored_resume.json"

# OpenAI client
client = None  # Will be set after load_dotenv()

# Token & cost accumulators
total_tokens_in  = 0
total_cost_in    = 0.0
total_tokens_out = 0
total_cost_out   = 0.0

# --------- Helper Functions ---------

def load_text(path: Path) -> str:
    """
    Load text content from a given file path.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Error reading file {path}: {e}")

def call_openai(messages: list, stage: str) -> str:
    """
    Call the OpenAI ChatCompletion API with the provided messages.
    Returns the assistant’s response content (trimmed).
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", 
            messages=messages, 
            temperature=0.3
        )
        content = resp.choices[0].message.content.strip()
        return content
    except Exception as e:
        raise RuntimeError(f"[{stage}] OpenAI call failed: {e}")

def write_to_report(section_title: str, content: str):
    """
    Append a section header and content to the report file.
    """
    try:
        with REPORT.open("a", encoding="utf-8") as report_file:
            report_file.write(f"## {section_title}\n\n{content}\n\n")
    except Exception as e:
        raise RuntimeError(f"Error writing to report: {e}")

def print_metrics(tokens_in: int, cost_in: float, tokens_out: int, cost_out: float):
    """
    Print token usage and cost for a pipeline stage.
    """
    print(f"Input Tokens: {tokens_in}, Cost: ${cost_in:.6f}")
    print(f"Output Tokens: {tokens_out}, Cost: ${cost_out:.6f}\n")

# --------- Two-Stage Pipeline ---------

def stage1_extract_keywords() -> str:
    """
    Stage 1: Analyze the Job Description (JD) to extract prioritized skills, keywords, technologies, and tone indicators.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    # Load JD and prompts
    jd_text       = load_text(JD_FILE)
    sys_prompt    = load_text(JD_SYS)
    user_template = load_text(JD_USER).replace("<JOB_DESCRIPTION_TEXT>", jd_text)

    # Estimate input tokens & cost
    tokens_in, cost_in = estimate_tokens_and_price(sys_prompt + user_template, "input")
    total_tokens_in  += tokens_in
    total_cost_in    += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_template},
        ],
        stage="stage1_extract_keywords",
    )

    # Estimate output tokens & cost
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out   += cost_out

    # Print & log
    print("\nStage 1 Complete: Extracted JD keywords.\n")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("Stage 1: Extracted JD Keywords", response)

    return response


def stage2_tailor_resume(jd_analysis: str, company: str, position: str) -> str:
    """
    Stage 2: Rewrite the candidate’s resume in JSON format to match the JD analysis,
    including target company and position details.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    # Load original resume and prompts
    resume_text    = load_text(RESUME_FILE)
    sys_prompt     = load_text(RT_SYS)
    user_template  = (
        load_text(RT_USER)
        .replace("<TARGET_COMPANY>", company)
        .replace("<TARGET_POSITION>", position)
        .replace("<KEY_TERMS_FROM_JD_ANALYSIS>", jd_analysis)
        .replace("<ORIGINAL_RESUME_TEXT>", resume_text)
    )

    # Estimate input tokens & cost
    tokens_in, cost_in = estimate_tokens_and_price(sys_prompt + user_template, "input")
    total_tokens_in  += tokens_in
    total_cost_in    += cost_in

    # API call
    response = call_openai(
        [
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_template},
        ],
        stage="stage2_tailor_resume",
    )

    # Estimate output tokens & cost
    tokens_out, cost_out = estimate_tokens_and_price(response, "output")
    total_tokens_out += tokens_out
    total_cost_out   += cost_out

    # Clean potential Markdown fences (```json) around the response
    cleaned = response.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove leading ```json (or ```) and trailing ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')):
        cleaned = cleaned.strip('"')

    # Validate JSON
    try:
        json_obj = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Stage 2: JSON parse failed: {e}\nRaw Response:\n{response}")

    # Print & log
    print("\nStage 2 Complete: Generated tailored resume JSON.\n")
    print_metrics(tokens_in, cost_in, tokens_out, cost_out)
    write_to_report("Stage 2: Tailored Resume JSON", cleaned)

    # Return the raw JSON string (for writing to file later)
    return cleaned


def run_pipeline(company: str, position: str, job_id: str):
    """
    Run the two-stage pipeline and generate final DOCX.
    """
    global total_tokens_in, total_cost_in, total_tokens_out, total_cost_out

    # Prepare results directory
    try:
        if RESULTS.exists():
            shutil.rmtree(RESULTS)
        RESULTS.mkdir(exist_ok=True)
    except Exception as e:
        print(f"Error preparing results directory: {e}")
        sys.exit(1)

    # Stage 1 → Stage 2
    try:
        jd_analysis = stage1_extract_keywords()
        tailored_json_str = stage2_tailor_resume(jd_analysis, company, position)
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)

    # Merge header and write final JSON to disk
    try:
        header_json = json.loads(load_text(HEADER_FILE))
        body_json   = json.loads(tailored_json_str)
        full_json   = {"header": header_json, **body_json}

        # Write final JSON
        TAILORED_JSON.write_text(json.dumps(full_json, indent=2), encoding="utf-8")

        # Append cost summary to report
        cost_summary = (
            "## Total Token Usage & Cost Summary\n"
            f"- Total Input Tokens: {total_tokens_in}, Total Input Cost: ${total_cost_in:.6f}\n"
            f"- Total Output Tokens: {total_tokens_out}, Total Output Cost: ${total_cost_out:.6f}\n"
        )
        write_to_report("Cost Summary", cost_summary)

        # Print total cost to console
        total_cost = total_cost_in + total_cost_out
        print(f"Total Cost for generating resume: ${total_cost:.6f}\n")

    except Exception as e:
        print(f"Error generating final JSON: {e}")
        sys.exit(1)

    # Generate DOCX from final JSON
    try:
        generate_docx_from_json(full_json, output_path=str(RESUMES / f"{company}_{position}_{job_id or ''}.docx"))
        # Optionally copy to Downloads
        dl = Path.home() / "Downloads"
        dl.mkdir(exist_ok=True)
        generate_docx_from_json(full_json, output_path=str(dl / f"{company}_{position}_resume.docx"))
        print(f"Generated DOCX: {RESUMES}/{company}_{position}_{job_id or ''}.docx")
    except Exception as e:
        print(f"Error generating DOCX: {e}")
        sys.exit(1)


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
