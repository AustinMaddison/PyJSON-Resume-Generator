<div align="center">

# PyJSON Resume Generator
  
You give it JSON, it spits out your resume as markup HTML and CSS. You can then render it as a PDF in your browser.  
Just like the name suggests, this tool is built with Python + JSON.  

</div>

## Features

- **Modern Harvard Style** - Professional, clean design that's ready for print
- **Position-specific resumes** - Automatically order projects by relevance for each job position
- **Live editing** - Watch mode rebuilds resumes on file changes
- **Multiple output formats** - HTML that can be printed to PDF with page breaks
- **Customizable sections** - Include or exclude sections as needed
- **Project limits** - Control how many projects appear per resume
- **Build statistics** - See performance metrics for each resume generation
- **Command-line controls** - Hugo-like command structure

<!-- ## Demo Videos

<!-- ### Live Editing with Watch Mode -->
<!-- Add link to demo video showing file changes and auto-reload -->
<!-- [Watch Mode Demo](https://example.com/demo-video) - See how changes to your JSON files instantly update your resume -->

<!-- ### Position-Based Project Ordering -->
<!-- Add link to demo video showing different resume outputs -->
<!-- [Position Ordering Demo](https://example.com/ordering-demo) - See how projects are automatically ordered by relevance -->

<!-- ### PDF Export with Page Breaks -->
<!-- Add link to demo video showing PDF export -->
<!-- [PDF Export Demo](https://example.com/pdf-demo) - See how to export to PDF with proper page breaks -->

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
