# Resume Refinery

Automatically analyze a job description and rewrite your resume to match it—generating both a JSON-formatted resume and a polished DOCX output.

## Features

-   **Two-Stage AI Pipeline**

    1. **Job Description Analysis**: Extracts prioritized skills, keywords, technologies, responsibilities, and tone indicators from any job posting.
    2. **Resume Tailoring**: Rewrites your existing resume (JSON) to integrate every extracted term—optimizing bullets, metrics, and skill sections—then outputs JSON and a professional DOCX.

-   **Strict JSON Output**  
    Ensures your tailored resume follows a consistent schema, ready for downstream processing or versioning.

-   **DOCX Generation**  
    Converts the final JSON into a clean, LaTeX-style .docx (via `python-docx`), with two-column headers, horizontal dividers, and formatted bullets.

-   **Cost Estimation**  
    Estimates token usage and cost for each stage (input vs. output) using `tiktoken`.

-   **Configurable Prompts**  
    All system/user prompts live in `prompts/`, so you can customize analysis or tailoring behavior.

## Getting Started

### Prerequisites

-   Python 3.8+
-   An OpenAI API key (set in your environment: `OPENAI_API_KEY`)
-   `pip install -r requirements.txt`

### Installation

```bash
git clone https://github.com/praneethravuri/resume-refinery.git
cd resume-refinery
pip install -r requirements.txt

Data Setup

    Create a data/ directory at the project root.

    Place your job description in data/job_description.txt.

    Place your original resume text in data/resume.txt.

    Create data/header_data.json with your personal header info.
    Example:

    {
      "name": "Your Name",
      "contact": [
        "Your location",
        "Phone number",
        "Email",
        "Your links..."
      ]
    }

Usage

Run the two-stage pipeline:

python main.py
# Enter prompts:
#   Company Name: <Target Company>
#   Position:     <Target Position>
#   Job ID (optional):

    Stage 1 writes an analysis section to results/report.md.

    Stage 2 writes results/tailored_resume.json and appends cost summary to report.md.

    A final DOCX is saved under:

        resumes/<company>_<position>_<job_id>.docx

        ~/Downloads/<company>_<position>_resume.docx


Output

    results/report.md – markdown report of JD analysis and cost summary

    results/tailored_resume.json – your resume rewritten in JSON

    resumes/*.docx – polished, formatted resume document

License

Apache 2.0
See LICENSE for details.
```
