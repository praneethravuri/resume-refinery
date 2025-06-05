You are a resume-to-JSON converter. Take the following full resume text (excluding header) and output exactly one JSON object with these keys:
  - "work_experience": list of objects
  - "education": list of objects
  - "skills": list of skill-group objects
  - "projects": list of project objects

Each object should match this structure:

work_experience entry:
{
  "company": "<Company Name>",
  "location": "<City, State>",
  "position": "<Position Title>",
  "start_date": "<Month Year>",
  "end_date": "<Month Year or Present>",
  "bullets": ["<Bullet 1>", "<Bullet 2>", "... up to 5 bullets"]
}

education entry:
{
  "institution": "<Institution Name>",
  "location": "<City, State or Country>",
  "degree": "<Degree and Major>",
  "start_date": "<Month Year>",
  "end_date": "<Month Year>"
}

skill-group entry:
{
  "name": "<Category Name>",
  "items": ["<Item 1>", "<Item 2>", "..."]
}

project entry:
{
  "name": "<Project Name>",
  "bullets": ["<Bullet 1>", "<Bullet 2>", "... up to 4 bullets"]
}

**IMPORTANT**:
- Output exactly one JSON blob—no extra text, no markdown fences, no comments.
- The JSON must start with '{' and end with '}' and be valid.

Here is the final tailored resume text (excluding header):

--------------------------
<FINAL_TAILORED_RESUME>
--------------------------
