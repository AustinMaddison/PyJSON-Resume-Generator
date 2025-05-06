<div align="center">

# 📄 PyJSON Resume Generator 📄
  
You give it JSON, it spits out your resume as markup HTML and CSS. You can then render it as a PDF in your browser.  
Just like the name suggests, this tool is built with Python + JSON.

_⚠️early development, enjoy this with caution⚠️_

</div>

## Features

- **Modern Harvard Style** - Professional, clean design that's ready for print
- **Position-specific resumes** - Order projects by relevance for each job position
- **Live editing** - Watch mode rebuilds resumes on file changes
- **Multiple output formats** - HTML that can be printed to PDF with page breaks
- **Customizable sections** - Include or exclude sections as needed
- **Project limits** - Control how many projects appear per resume
- **Command-line controls** - Hugo-like command structure

## Demo Videos

### Live Editing with Watch Mode
See how changes to your JSON files update the resume.

https://github.com/user-attachments/assets/467ea9f9-7451-405f-871c-854853c79d7b


### Position-Based Project Ordering
See you can order projects for a given position by relevance or whatever you feel fit.

https://github.com/user-attachments/assets/2d7a6af3-a838-42e9-b45f-7cb5b08faf20


### PDF Export with Page Breaks
See how to export to PDF and section items break without producing widows and orphans.

https://github.com/user-attachments/assets/6b514cf7-a525-45cc-b45e-1c88eadf803a



## Installation

### Prerequisites

- Python 3.6+
- Node.js and npm (for CSS processing)

### Clone the Repository

```bash
git clone https://github.com/AustinMaddison/PyJSON-Resume-Generator.git
cd PyJSON-Resume-Generator
```

### Install Dependencies

```bash
npm install
```

```bash
pip install jinja2 flask watchdog
```

## Usage

### Basic Build

```bash
python resume-generator.py build
```

### Build and Watch for Changes

```bash
python resume-generator.py build -w
```

### Run Server Only (No Building)

```bash
python resume-generator.py server
```
Remember you can still open resume .html builds directly from file without running server.

### Customizing Output

#### Exclude certain sections
```bash
python resume-generator.py build --exclude=certifications,education
```

#### Include only specific sections
```bash
python resume-generator.py build --sections=header,summary,experience,projects
```

#### Limit number of projects
```bash
python resume-generator.py build --max-projects=3
```

#### Change JSON file paths
```bash
python resume-generator.py build --base-json=./custom/base.json --projects-json=./custom/projects.json --positions-json=./custom/positions.json
```

#### Change output directory and port
```bash
python resume-generator.py build --output-dir=./output --port=8080
```

## JSON Configuration

The tool uses three main JSON files:

- **base.json** - Your personal information, education, work experience, skills, etc.
- **projects.json** - Details about all your projects
- **positions.json** - Job positions with custom project ordering

### Example Position Configuration

```json
{
  "job-positions": [
    {
      "title": "Frontend Engineer",
      "summary": "Crafts responsive, user-focused interfaces...",
      "project-order": [
        "Project Name 1",
        "Project Name 2",
        "Project Name 3"
      ]
    }
  ]
}
```

## PDF Export with Page Breaks

The generated HTML includes CSS to properly handle page breaks when printed to PDF:

```css
.section {
  break-before: page; /* Forces page break before each section */
  page-break-before: always; /* For older browsers */
}

.keep-together {
  break-inside: avoid; /* Prevents breaking within a section */
  page-break-inside: avoid; /* For older browsers */
}
```

To export as PDF, open the resume in your browser and use the Print to PDF option (Ctrl+P or Cmd+P).

## Roadmap

- [x] Modern Harvard Style
- [x] JSON input for base and project data
- [x] Position-specific project ordering
- [x] Command-based structure (build, server)
- [x] Build statistics
- [x] Index page with links to all resumes
- [x] File watching with auto-rebuild (`-w` flag)
- [x] Robust error handling for missing files
- [x] Limit total SSE connections
- [ ] Adjust ordering of any section using weights
- [ ] Break up JSON inputs into multiple files
- [ ] Preview resume thumbnails on index page
- [ ] Support for multiple theme templates
- [ ] Print-specific optimizations

## License
MIT
