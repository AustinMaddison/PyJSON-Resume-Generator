<div align="center">

# PyJSON Resume Generator
  
You give it JSON, it spits out your resume as markup HTML and CSS. You can then rendered it as a PDF in your browser.  
Just like the name suggests, this tool is built with Python + JSON.  

__⚠️ Super Experimental: Use with caution.⚠️__

</div>

<div align="center">

<div align="left">

## Install and Run

### Git Clone
```bash
https://github.com/AustinMaddison/PyJSON-Resume-Generator.git
```

### Install Dependencies
```bash
npm install
```
```bash
pip install jinja2 flask watchdog
```

### Run
```bash
python resume-generator.py
```

## Usage

#### Exclude certain sections
```bash
python resume-generator.py --exclude=certifications,education
```

#### Include only specific sections
```bash
python resume-generator.py --sections=header,summary,experience,projects
```

#### Limit number of projects
```bash
python resume-generator.py --max-projects=3
```

#### Change JSON file paths
```bash
python resume-generator.py --base-json=./custom/base.json --projects-json=./custom/projects.json
```

### Change output directory and port
```bash
python resume-generator.py --output-dir=./output --port=8080
```
## Features
- [x] Modern Harvard Style
- [x] JSON input base + project data
- [x] Project items ordered based on resume's job position.
- [ ] Be able to adjust the ordering of any section using a map or weights.
- [ ] The ability to break up the input JSON's to as many files as a user wants.
- [ ] Have a master json configuration that can order sections and more.
- [x] Overide default configuration using program arguments.
- [x] Index page.
- [ ] Preview resume on index page.
- [x] Live updates on file edit (Limited to 5 tabs at a time).
